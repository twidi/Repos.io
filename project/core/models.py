from datetime import datetime, timedelta

from django.db import models
from django.contrib.auth.models import User

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField

from core.backends import BACKENDS, get_backend
from core.exceptions import SaveForbiddenInBackend
from core.managers import AccountManager, RepositoryManager

BACKENDS_CHOICES = Choices(*BACKENDS.keys())

MIN_FETCH_DELTA = timedelta(minutes=30)
MIN_FETCH_RELATED_DELTA = timedelta(minutes=30)

class SyncableModel(TimeStampedModel):
    """
    A base model usable for al objects syncable within a provider.
    TimeStampedModel add `created` and `modified` fields, auto updated
    when needed.
    """

    STATUS = Choices(
        ('creating', 'Creating'),              # just created
        ('to_update', 'To Update'),            # need to be updated
        ('need_related', 'Related to update'), # related need to be updated
        ('updating', 'Updating'),              # update running from the backend
        ('ok', 'Ok'),                          # everything ok ok
    )

    # The backend from where this object come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES)

    # A status field, using STATUS
    status = StatusField(max_length=10)

    # Date of last own full fetch
    last_fetch = models.DateTimeField(blank=True, null=True)

    # Fetch operations
    fetch_related_operations = ()

    class Meta:
        abstract = True


    def __unicode__(self):
        return u'%s' % self.slug

    def __init__(self, *args, **kwargs):
        """
        Init some internal values
        """
        super(SyncableModel, self).__init__(*args, **kwargs)
        if not self.status:
            self.status = self.STATUS.creating
        self._block_save = False

    def get_backend(self):
        """
        Return (and create and cache if needed) the backend object
        """
        if not hasattr(self, '_backend'):
            self._backend = get_backend(self.backend)
        return self._backend
        self.save()

    def get_new_status(self):
        """
        Return the status to be saved
        """
        raise NotImplementedError('Implement in subclasses')

    def update_status(self):
        """
        Simply get and save the current status (can be updated because of datetime delta)
        """
        self.status = self.get_new_status()
        self.save()

    def save(self, *args, **kwargs):
        """
        Save is forbidden while in the backend...
        Also update the status before saving
        """
        if self._block_save:
            raise SaveForbiddenInBackend()

        self.status = self.get_new_status()
        super(SyncableModel, self).save(*args, **kwargs)

    def fetch_needed(self):
        """
        Check if a fetch is needed for this object.
        It's True if it's a new object, if the status is "to_update" or
        if it's ok and fetched long time ago
        """
        if not self.id:
            return True
        if self.status in (self.STATUS.to_update,):
            return True
        if self.status == 'ok' and self.last_fetch < datetime.now() - MIN_FETCH_DELTA:
            return True
        return False

    def fetch_related_needed(self):
        """
        Check if we need to update some related objects
        """
        if not self.id:
            return False
        return self.get_new_status() in (self.STATUS.to_update, self.STATUS.need_related)

    def fetch_related(self, limit=None):
        """
        If the object has some related content that need to be fetched, do
        it, but limit the fetch to the given limit (default 1)
        Returns the number of operations done
        """
        if not self.fetch_related_needed():
            return 0
        done = 0
        for operation_name in self.fetch_related_operations:
            operation = getattr(self, 'fetch_%s' % operation_name)
            if operation():
                done += 1
            if limit and done >= limit:
                break
        if done:
            self.save()
        return done


class Account(SyncableModel):
    """
    Represent an account from a backend
    How load an account, the good way :
        Account.objects.get_or_new(backend, slug)
    """

    # Basic informations

    # The slug for this account (text identifier for the provider : login, username...)
    slug = models.SlugField(max_length=255)
    # The fullname
    name = models.CharField(max_length=255, blank=True, null=True)
    # The avatar url
    avatar = models.URLField(max_length=255, blank=True, null=True)
    # The account's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # Since when this account exists on the provider
    since = models.DateField(blank=True, null=True)
    # Is this account private ?
    private = models.NullBooleanField(blank=True, null=True)

    # If there is a user linked to this account
    user = models.ForeignKey(User, related_name='accounts', blank=True, null=True, on_delete=models.SET_NULL)

    # The last access_token for authenticated requests
    access_token = models.TextField(blank=True, null=True)

    # Followers informations

    # From the backed
    official_followers_count = models.PositiveIntegerField(blank=True, null=True)
    official_following_count = models.PositiveIntegerField(blank=True, null=True)
    # Saved counts
    followers_count = models.PositiveIntegerField(blank=True, null=True)
    following_count = models.PositiveIntegerField(blank=True, null=True)
    followers_count_modified = models.DateTimeField(blank=True, null=True)
    following_count_modified = models.DateTimeField(blank=True, null=True)
    # List of followed Account object
    following = models.ManyToManyField('self', related_name='followers', symmetrical=False)

    # List of owned/watched repositories
    repositories = models.ManyToManyField('Repository', related_name='followers')
    # Saved count
    repositories_count = models.PositiveIntegerField(blank=True, null=True)
    repositories_count_modified = models.DateTimeField(blank=True, null=True)

    # The default manager
    objects = AccountManager()

    # Fetch operations
    fetch_related_operations = ('following', 'followers', 'repositories',)

    class Meta:
        unique_together = (('backend', 'slug'),)


    def get_new_status(self):
        """
        Return the status to be saved
        """
        # a related list need to be fetched ?
        if None in (self.following_count, self.followers_count, self.repositories_count):
            return self.STATUS.need_related
        # a related list need to be updated ?
        for operation in ('following', 'followers', 'repositories'):
            field = '%s_count_modified' % operation
            date = getattr(self, field)
            if not date or date < datetime.now() - MIN_FETCH_RELATED_DELTA:
                return self.STATUS.need_related
        return self.STATUS.ok

    def fetch(self):
        """
        Fetch data from the provider
        """
        self._block_save = True
        self.get_backend().user_fetch(self)
        self._block_save = False
        self.last_fetch = datetime.now()

        self.save()

    def fetch_following(self):
        """
        Fetch the accounts followed by this account
        """
        # get all previous following
        old_following = dict((a.slug, a) for a in self.following.all())

        # get and save new followings
        following_list = self.get_backend().user_following(self)
        new_following = {}
        for gaccount in following_list:
            account = self.add_following(gaccount, False)
            if account:
                new_following[account.slug] = account

        # remove old following
        removed = set(old_following.keys()).difference(set(new_following.keys()))
        for slug in removed:
            self.remove_following(old_following[slug], update_self_count=False)

        self.following_count_modified = datetime.now()
        self.update_following_count(save=True)

        return True

    def add_following(self, account, update_self_count):
        """
        Try to add the account described by `account` as followed by
        the current account.
        `account` can be an Account object, or a dict. In this case, it
        must contain a `slug` field.
        All other fields in `account` will only be used to fill
        the new Account fields if we must create it.
        """
        # we have a dict : get the account
        if isinstance(account, dict):
            if not account.get('slug', False):
                return None
            account = Account.objects.get_or_new(
                self.backend, account.pop('slug'), **account)

        # we have something else but an account : exit
        elif not isinstance(account, Account):
            return None

        # save the account if it's a new one
        is_new = not bool(account.id)
        if is_new:
            account.followers_count = 1
            account.save()

        # add the following
        self.following.add(account)

        # update the count if we can
        if update_self_count:
            self.update_following_count(save=True)

        # update the followers count for the other account
        if not is_new:
            account.update_followers_count(save=True)

        return account

    def remove_following(self, account, update_self_count):
        """
        Remove the given account from the ones followed by
        the current account
        """
        # we have something else but an account : exit
        if not isinstance(account, Account):
            return

        # remove the following
        self.following.remove(account)

        # update the count if we can
        if update_self_count:
            self.update_following_count(save=True)

        # update the followers count for the other account
        account.update_followers_count(save=True)

        return account

    def update_following_count(self, save):
        """
        Update the saved following count
        """
        self.following_count = self.following.count()
        if save:
            self.save()

    def fetch_followers(self):
        """
        Fetch the accounts following this account
        """
        # get all previous followers
        old_followers = dict((a.slug, a) for a in self.followers.all())

        # get and save new followings
        followers_list = self.get_backend().user_followers(self)
        new_followers = {}
        for gaccount in followers_list:
            account = self.add_follower(gaccount, False)
            if account:
                new_followers[account.slug] = account

        # remove old followers
        removed = set(old_followers.keys()).difference(set(new_followers.keys()))
        for slug in removed:
            self.remove_follower(old_followers[slug], update_self_count=False)

        self.followers_count_modified = datetime.now()
        self.update_followers_count(save=True)

        return True

    def add_follower(self, account, update_self_count):
        """
        Try to add the account described by `account` as follower of
        the current account.
        `account` can be an Account object, or a dict. In this case, it
        must contain a `slug` field.
        All other fields in `account` will only be used to fill
        the new Account fields if we must create it.
        """
        # we have a dict : get the account
        if isinstance(account, dict):
            if not account.get('slug', False):
                return None
            account = Account.objects.get_or_new(
                self.backend, account.pop('slug'), **account)

        # we have something else but an account : exit
        elif not isinstance(account, Account):
            return None

        # save the account if it's a new one
        is_new = not bool(account.id)
        if is_new:
            account.following_count = 1
            account.save()

        # add the follower
        self.followers.add(account)

        # update the count if we can
        if update_self_count:
            self.update_followers_count(save=True)

        # update the following count for the other account
        if not is_new:
            account.update_following_count(save=True)

        return account

    def remove_follower(self, account, update_self_count):
        """
        Remove the given account from the ones following
        the current account
        """
        # we have something else but an account : exit
        if not isinstance(account, Account):
            return

        # remove the follower
        self.followers.remove(account)

        # update the count if we can
        if update_self_count:
            self.update_followers_count(save=True)

        # update the following count for the other account
        account.update_following_count(save=True)

    def update_followers_count(self, save):
        """
        Update the saved followers count
        """
        self.followers_count = self.followers.count()
        if save:
            self.save()

    def fetch_repositories(self):
        """
        Fetch the repositories owned/watched by this account
        """
        # get all previous repositories
        old_repositories = dict((r.project, r) for r in self.repositories.all())

        # get and save new repositories
        repositories_list = self.get_backend().user_repositories(self)
        new_repositories = {}
        for grepo in repositories_list:
            repository = self.add_repository(grepo, False)
            if repository:
                new_repositories[repository.project] = repository

        # remove old repositories
        removed = set(old_repositories.keys()).difference(set(new_repositories.keys()))
        for project in removed:
            self.remove_repository(old_repositories[project], update_self_count=False)

        self.repositories_count_modified = datetime.now()
        self.update_repositories_count(save=True)

        return True

    def add_repository(self, repository, update_self_count):
        """
        Try to add the repository described by `repository` as one
        owner/watched by the current account.
        `repository` can be an Repository object, or a dict. In this case, it
        must contain enouhg identifiers (see `needed_repository_identifiers`)
        All other fields in `repository` will only be used to fill
        the new Repository fields if we must create it.
        """
        # we have a dict : get the repository
        if isinstance(repository, dict):
            try:
                self.get_backend().assert_valid_repository_identifiers(**repository)
            except:
                return None
            else:
                repository = Repository.objects.get_or_new(
                    self.backend, repository.pop('project', None), **repository)

        # we have something else but a repository : exit
        elif not isinstance(repository, Repository):
            return None

        # save the repository if it's a new one
        is_new = not bool(repository.id)
        if is_new:
            repository.followers_count = 1
            repository.save()

        # add the repository
        self.repositories.add(repository)

        # update the count if we can
        if update_self_count:
            self.update_repositories_count(save=True)

        # update the followers count for the repository
        if not is_new:
            repository.update_followers_count(save=True)

        return repository

    def remove_repository(self, repository, update_self_count):
        """
        Remove the given account from the ones the user own/watch
        """
        # we have something else but a repository : exit
        if not isinstance(repository, Repository):
            return

        # remove the repository
        self.repositories.remove(repository)

        # update the count if we can
        if update_self_count:
            self.update_repositories_count(save=True)

        # update the followers count for the repository
        repository.update_followers_count(save=True)

    def update_repositories_count(self, save):
        """
        Update the saved repositories count
        """
        self.repositories_count = self.repositories.count()
        if save:
            self.save()

class Repository(SyncableModel):
    """
    Represent a repository from a backend
    How load a repository, the good way :
        Repository.objects.get_or_new(backend, project_name)
    """

    # Basic informations

    # The slug for this repository (text identifier for the provider)
    slug = models.SlugField(max_length=255)
    # The fullname of this repository
    name = models.CharField(max_length=255, blank=True, null=True)
    # The web url for this repository
    url = models.URLField(max_length=255, blank=True, null=True)
    # The description of this repository
    description = models.TextField(blank=True, null=True)
    # The project's logo url
    logo = models.URLField(max_length=255, blank=True, null=True)
    # The project's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # The canonical project name (example twidi/myproject)
    project = models.TextField()
    # Is this repository private ?
    private = models.NullBooleanField(blank=True, null=True)

    # Owner

    # The owner's "slug" of this project, from the backend
    official_owner = models.CharField(max_length=255, blank=True, null=True)
    # The Account object whom own this Repository
    owner = models.ForeignKey(Account, related_name='own_repositories', blank=True, null=True, on_delete=models.SET_NULL)

    # Forks & followers informations

    # Forks count (from the backend)
    official_forks_count = models.PositiveIntegerField(blank=True, null=True)
    # Project name of the repository from which this repo is the fork (from the backend)
    official_fork_of = models.TextField(blank=True, null=True)
    # Followers count (from the backend)
    official_followers_count = models.PositiveIntegerField(blank=True, null=True)
    # Saved count
    followers_count = models.PositiveIntegerField(blank=True, null=True)
    followers_count_modified = models.DateTimeField(blank=True, null=True)

    # Set to True if this Repository is a fork of another
    is_fork = models.NullBooleanField(blank=True, null=True)
    # The Repository object from which this repo is the fork
    parent_fork = models.ForeignKey('self', related_name='forks', blank=True, null=True, on_delete=models.SET_NULL)

    # The default manager
    objects = RepositoryManager()

    # Fetch operations
    fetch_related_operations = ('owner', 'parent_fork', 'followers')


    class Meta:
        unique_together = (('backend', 'official_owner', 'slug'),)


    def __unicode__(self):
        return u'%s' % self.get_project()

    def get_new_status(self):
        """
        Return the status to be saved
        """
        # need the parents fork's name ?
        if self.is_fork and not self.official_fork_of:
            return self.STATUS.to_update
        # need the owner (or to remove it) ?
        if self.official_owner and not self.owner_id:
            return self.STATUS.need_related
        if not self.official_owner and self.owner_id:
            return self.STAUTS.need_related
        # need the parent fork ?
        if self.is_fork and not self.parent_fork_id:
            return self.STATUS.need_related
        # a related list need to be fetched ?
        if None in (self.followers_count,):
            return self.STATUS.need_related
        # a related list need to be updated ?
        for operation in ('followers',):
            field = '%s_count_modified' % operation
            date = getattr(self, field)
            if not date or date < datetime.now() - MIN_FETCH_RELATED_DELTA:
                return self.STATUS.need_related
        return self.STATUS.ok

    def get_project(self):
        """
        Return the project name (sort of identifier)
        """
        return self.project or self.get_backend().repository_project(self)

    def fetch(self):
        """
        Fetch data from the provider
        """
        self._block_save = True
        self.get_backend().repository_fetch(self)
        self._block_save = False
        self.last_fetch = datetime.now()

        self.save()

    def save(self, *args, **kwargs):
        """
        Update the project field
        """
        if not self.project:
            self.project = self.get_project()
        super(Repository, self).save(*args, **kwargs)

    def fetch_owner(self):
        """
        Create or update the repository's owner
        """
        if not self.official_owner:
            return False

        save_needed = False
        fetched = False

        if not self.owner_id and not self.owner:
            save_needed = True
            owner = Account.objects.get_or_new(self.backend, self.official_owner)
        else:
            owner = self.owner

        if owner.fetch_needed():
            owner.fetch()
            fetched = True

        if save_needed:
            if not self.owner_id:
                self.owner = owner
            self.save()
            self.followers.add(self.owner)

        return fetched

    def fetch_parent_fork(self):
        """
        Create of update the parent fork, only if needed and if we have the
        parent fork's name
        """
        if not (self.is_fork and self.official_fork_of):
            if self.parent_fork_id:
                self.parent_fork = None
                self.save()
            return False

        save_needed = False
        fetched = False

        if not self.parent_fork_id:
            save_needed = True
            parent_fork = Repository.objects.get_or_new(self.backend,
                project=self.official_fork_of)
        else:
            parent_fork = self.parent_fork

        if parent_fork.fetch_needed():
            parent_fork.fetch()
            fetched = True

        if save_needed:
            if not self.parent_fork_id:
                self.parent_fork = parent_fork
            self.save()

        return fetched

    def fetch_followers(self):
        """
        Fetch the accounts following this repository
        """
        # get all previous followers
        old_followers = dict((a.slug, a) for a in self.followers.all())

        # get and save new followings
        followers_list = self.get_backend().repository_followers(self)
        new_followers = {}
        for gaccount in followers_list:
            account = self.add_follower(gaccount, False)
            if account:
                new_followers[account.slug] = account

        # remove old followers
        removed = set(old_followers.keys()).difference(set(new_followers.keys()))
        for slug in removed:
            self.remove_follower(old_followers[slug], update_self_count=False)

        self.followers_count_modified = datetime.now()
        self.update_followers_count(save=True)

        return True

    def add_follower(self, account, update_self_count):
        """
        Try to add the account described by `account` as follower of
        the current repository.
        `account` can be an Account object, or a dict. In this case, it
        must contain a `slug` field.
        All other fields in `account` will only be used to fill
        the new Account fields if we must create it.
        """
        # we have a dict : get the account
        if isinstance(account, dict):
            if not account.get('slug', False):
                return None
            account = Account.objects.get_or_new(
                self.backend, account.pop('slug'), **account)

        # we have something else but an account : exit
        elif not isinstance(account, Account):
            return None

        # save the account if it's a new one
        is_new = not bool(account.id)
        if is_new:
            account.repositories_count = 1
            account.save()

        # add the follower
        self.followers.add(account)

        # update the count if we can
        if update_self_count:
            self.update_followers_count(save=True)

        # update the repositories count for the account
        if not is_new:
            account.update_repositories_count(save=True)

        return account

    def remove_follower(self, account, update_self_count):
        """
        Remove the given account from the ones following
        the Repository
        """
        # we have something else but an account : exit
        if not isinstance(account, Account):
            return

        # remove the follower
        self.followers.remove(account)

        # update the count if we can
        if update_self_count:
            self.update_followers_count(save=True)

        # update the following count for the other account
        account.update_repositories_count(save=True)

    def update_followers_count(self, save):
        """
        Update the saved followers
        """
        self.followers_count = self.followers.count()
        if save:
            self.save()
