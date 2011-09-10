from datetime import datetime, timedelta
from copy import copy

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField

from core.backends import BACKENDS, get_backend
from core.managers import AccountManager, RepositoryManager
from core.utils import slugify
from core.exceptions import BackendError, MultipleBackendError

BACKENDS_CHOICES = Choices(*BACKENDS.keys())

class SyncableModel(TimeStampedModel):
    """
    A base model usable for al objects syncable within a provider.
    TimeStampedModel add `created` and `modified` fields, auto updated
    when needed.
    """

    STATUS = Choices(
        ('creating', 'Creating'),                  # just created
        ('fetch_needed', 'Need to fetch object'),  # need to be updated
        ('need_related', 'Need to fetch related'), # related need to be updated
        ('updating', 'Updating'),                  # update running from the backend (not used)
        ('ok', 'Ok'),                              # everything ok ok
    )

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'MIN_FETCH_DELTA', timedelta(minutes=30))
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'MIN_FETCH_RELATED_DELTA', timedelta(minutes=30))
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'MIN_FETCH_DELTA_NEEDED', timedelta(hours=6))
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'MIN_FETCH_RELATED_DELTA_NEEDED', timedelta(hours=6))

    # The backend from where this object come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES)

    # A status field, using STATUS
    status = StatusField(max_length=15)

    # Date of last own full fetch
    last_fetch = models.DateTimeField(blank=True, null=True)

    # Fetch operations
    backend_prefix = ''
    related_operations = (
        # name, with count, with modified
    )

    class Meta:
        abstract = True


    def __unicode__(self):
        return u'%s' % self.slug

    def is_new(self):
        """
        Return True if this object is a new one not saved in db
        """
        return self.status == 'creating' or not self.pk

    def __init__(self, *args, **kwargs):
        """
        Init some internal values
        """
        super(SyncableModel, self).__init__(*args, **kwargs)
        if not self.status:
            self.status = self.STATUS.creating

    def get_backend(self):
        """
        Return (and create and cache if needed) the backend object
        """
        if not hasattr(self, '_backend'):
            self._backend = get_backend(self.backend)
        return self._backend

    def get_new_status(self):
        """
        Return the status to be saved
        """
        # no id, object is in creating mode
        if not self.id:
            return self.STATUS.creating

        # Never fetched of fetched "long" time ago => fetch needed
        if not self.last_fetch or self.last_fetch < datetime.now() - self.MIN_FETCH_DELTA_NEEDED:
            return self.STATUS.fetch_needed

        # Work on each related field
        for name, with_count, with_modified in self.related_operations:
            if with_count:
                # count never updated => fetch of related needed
                count = getattr(self, '%s_count' % name)
                if count is None:
                    return self.STATUS.need_related
            if with_modified:
                # modified date never updated or too old => fetch of related needed
                date = getattr(self, '%s_modified' % name)
                if not date or date < datetime.now() - self.MIN_FETCH_RELATED_DELTA_NEEDED:
                    return self.STATUS.need_related

        # else, default ok
        return self.STATUS.ok

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
        self.status = self.get_new_status()
        super(SyncableModel, self).save(*args, **kwargs)

    def fetch_needed(self):
        """
        Check if a fetch is needed for this object.
        It's True if it's a new object, if the status is "fetch_needed" or
        if it's ok and fetched long time ago
        """
        self.status = self.get_new_status()
        if self.status  in (self.STATUS.creating, self.STATUS.fetch_needed,):
            return True
        return False

    def fetch_allowed(self):
        """
        Return True if a new fetch is allowed (not too recent)
        """
        return bool(not self.last_fetch or self.last_fetch < datetime.now() - self.MIN_FETCH_DELTA)

    def fetch(self):
        """
        Fetch data from the provider (need to be implemented in subclass)
        """
        return self.fetch_allowed()

    def fetch_related_needed(self):
        """
        Check if we need to update some related objects
        """
        self.status = self.get_new_status()
        if self.status in (self.STATUS.creating,):
            return False
        return self.status in (self.STATUS.fetch_needed, self.STATUS.need_related)

    def fetch_related_allowed(self):
        """
        Return True if a new fetch of related is allowed (if at least one is
        not too recent)
        """
        for name, with_count, with_modified in self.related_operations:
            if not with_modified:
                continue
            if self.fetch_related_allowed_for(name):
                return True

        return False

    def last_fetch_related(self):
        """
        Get the last related modified date
        """
        last = None
        backend = self.get_backend()
        for name, with_count, with_modified in self.related_operations:
            if not with_modified:
                continue
            if not backend.supports(self.backend_prefix + name):
                continue
            date = getattr(self, '%s_modified' % name)
            if last is None or date > last:
                last = date

        return last

    def fetch_related_allowed_for(self, operation):
        """
        Return True if a new fetch of a related is allowed(if not too recent)
        """
        try:
            name, with_count, with_modified = [op for op in self.related_operations if op[0] == operation][0]
        except:
            return False

        if not with_modified:
            return True

        if not self.get_backend().supports(self.backend_prefix + operation):
            return False
        date = getattr(self, '%s_modified' % operation)
        if not date or date < datetime.now() - self.MIN_FETCH_RELATED_DELTA:
            return True

        return False

    def fetch_related(self, limit=None):
        """
        If the object has some related content that need to be fetched, do
        it, but limit the fetch to the given limit (default 1)
        Returns the number of operations done
        """
        done = 0
        exceptions = []
        for operation in self.related_operations:
            if not self.fetch_related_allowed_for(operation[0]):
                continue
            action = getattr(self, 'fetch_%s' % operation[0])

            try:
                #print "%s : update %s" % (self, operation[0])
                if action():
                    done += 1
            except BackendError, e:
                exceptions.append(e)

            if limit and done >= limit:
                break
        if done:
            self.save()

        # handle one or many exceptions
        if exceptions:
            if len(exceptions) == 1:
                raise exceptions[0]
            else:
                raise MultipleBackendError([e.message for e in exceptions])

        return done

    def update_many_fields(self, **params):
        """
        Update many fields on the object using ones
        found in `params`
        """
        if not params:
            return
        updated = 0
        for param, value in params.items():
            if not hasattr(self, param):
                continue
            field = getattr(self, param)
            if not callable(field) and field != value:
                #print "%s : update %s from [%s] to [%s]" % (self, param, getattr(self,param), value)
                setattr(self, param, value)
                updated += 1
        if updated:
            self.save()
        return updated

    def haystack_context(self):
        """
        Return a dict haystack can use to render a template for this object,
        as it does not, obviously, handle request and no context processors
        """
        return dict(
            STATIC_URL = settings.STATIC_URL,
        )


class Account(SyncableModel):
    """
    Represent an account from a backend
    How load an account, the good way :
        Account.objects.get_or_new(backend, slug)
    """

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'ACCOUNT_MIN_FETCH_DELTA', SyncableModel.MIN_FETCH_DELTA)
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'ACCOUNT_MIN_FETCH_RELATED_DELTA', SyncableModel.MIN_FETCH_RELATED_DELTA)
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'ACCOUNT_MIN_FETCH_DELTA_NEEDED', SyncableModel.MIN_FETCH_DELTA_NEEDED)
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'ACCOUNT_MIN_FETCH_RELATED_DELTA_NEEDED', SyncableModel.MIN_FETCH_RELATED_DELTA_NEEDED)

    # Basic informations

    # The slug for this account (text identifier for the provider : login, username...)
    slug = models.SlugField(max_length=255)
    # The same, adapted for sorting
    slug_sort = models.SlugField(max_length=255)
    # The fullname
    name = models.CharField(max_length=255, blank=True, null=True)
    # The backend url
    url = models.URLField(max_length=255, blank=True, null=True)
    # The avatar url
    avatar = models.URLField(max_length=255, blank=True, null=True)
    # The account's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # Since when this account exists on the provider
    since = models.DateField(blank=True, null=True)
    # Is this account private ?
    private = models.NullBooleanField(blank=True, null=True)
    # Account dates
    official_created = models.DateTimeField(blank=True, null=True)

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
    followers_modified = models.DateTimeField(blank=True, null=True)
    following_modified = models.DateTimeField(blank=True, null=True)
    # List of followed Account object
    following = models.ManyToManyField('self', related_name='followers', symmetrical=False)

    # List of owned/watched repositories
    repositories = models.ManyToManyField('Repository', related_name='followers')
    # Saved count
    repositories_count = models.PositiveIntegerField(blank=True, null=True)
    repositories_modified = models.DateTimeField(blank=True, null=True)

    # The default manager
    objects = AccountManager()

    # Fetch operations
    backend_prefix = 'user_'
    related_operations = (
        # name, with count, with modified
        ('following', True, True),
        ('followers', True, True),
        ('repositories', True, True),
    )

    class Meta:
        unique_together = (('backend', 'slug'),)

    def fetch(self):
        """
        Fetch data from the provider
        """
        if not super(Account, self).fetch():
            return False

        self.get_backend().user_fetch(self)
        self.last_fetch = datetime.now()

        self.save()
        return True

    def save(self, *args, **kwargs):
        """
        Update the project and sortable fields
        """
        if self.slug:
            self.slug_sort = slugify(self.slug)
        super(Account, self).save(*args, **kwargs)

    def fetch_following(self):
        """
        Fetch the accounts followed by this account
        """
        if not self.get_backend().supports('user_following'):
            return False

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

        self.following_modified = datetime.now()
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
        is_new = account.is_new()
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
        if not self.get_backend().supports('user_followers'):
            return False

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

        self.followers_modified = datetime.now()
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
        is_new = account.is_new()
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
        if not self.get_backend().supports('user_repositories'):
            return False

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

        self.repositories_modified = datetime.now()
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
        is_new = repository.is_new()
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

    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        if not url_type.startswith('account'):
            url_type = 'account_%s' % url_type
        params = copy(kwargs)
        if 'backend' not in params:
            params['backend'] = self.backend
        if 'slug' not in params:
            params['slug'] = self.slug
        return (url_type, (), params)

    @models.permalink
    def get_absolute_url(self):
        """
        Home page url for this Account
        """
        return self._get_url('home')

    @models.permalink
    def get_followers_url(self):
        """
        Followers page url for this Account
        """
        return self._get_url('followers')

    @models.permalink
    def get_following_url(self):
        """
        Following page url for this Account
        """
        return self._get_url('following')

    @models.permalink
    def get_repositories_url(self):
        """
        Repositories page url for this Account
        """
        return self._get_url('repositories')

    def following_slugs(self):
        """
        Return the following as a list of slugs
        """
        if not hasattr(self, '_following_slugs'):
            self._following_slugs = [f.slug for f in self.following.all()]
        return self._following_slugs

    def followers_slugs(self):
        """
        Return the followers as a list of slugs
        """
        if not hasattr(self, '_followers_slugs'):
            self._followers_slugs = [f.slug for f in self.followers.all()]
        return self._followers_slugs

class Repository(SyncableModel):
    """
    Represent a repository from a backend
    How load a repository, the good way :
        Repository.objects.get_or_new(backend, project_name)
    """

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'REPOSITORY_MIN_FETCH_DELTA', SyncableModel.MIN_FETCH_DELTA)
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'REPOSITORY_MIN_FETCH_RELATED_DELTA', SyncableModel.MIN_FETCH_RELATED_DELTA)
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'REPOSITORY_MIN_FETCH_DELTA_NEEDED', SyncableModel.MIN_FETCH_DELTA_NEEDED)
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'REPOSITORY_MIN_FETCH_RELATED_DELTA_NEEDED', SyncableModel.MIN_FETCH_RELATED_DELTA_NEEDED)

    # Basic informations

    # The slug for this repository (text identifier for the provider)
    slug = models.SlugField(max_length=255)
    # The same, adapted for sorting
    slug_sort = models.CharField(max_length=255, blank=True, null=True)
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
    # The same, adapted for sorting
    project_sort = models.TextField()
    # Is this repository private ?
    private = models.NullBooleanField(blank=True, null=True)
    # Repository dates
    official_created = models.DateTimeField(blank=True, null=True)
    official_modified = models.DateTimeField(blank=True, null=True)

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
    followers_modified = models.DateTimeField(blank=True, null=True)

    # Set to True if this Repository is a fork of another
    is_fork = models.NullBooleanField(blank=True, null=True)
    # The Repository object from which this repo is the fork
    parent_fork = models.ForeignKey('self', related_name='forks', blank=True, null=True, on_delete=models.SET_NULL)

    # List of owned/watched contributors
    contributors = models.ManyToManyField('Account', related_name='contributing')
    # Saved count
    contributors_count = models.PositiveIntegerField(blank=True, null=True)
    contributors_modified = models.DateTimeField(blank=True, null=True)

    # more about the content of the reopsitory
    default_branch = models.CharField(max_length=255, blank=True, null=True)
    readme = models.TextField(blank=True, null=True)
    readme_type = models.CharField(max_length=10, blank=True, null=True)
    readme_modified = models.DateTimeField(blank=True, null=True)

    # The default manager
    objects = RepositoryManager()

    # Fetch operations
    backend_prefix = 'repository_'
    related_operations = (
        # name, with count, with modified
        ('owner', False, False),
        ('parent_fork', False, False),
        ('followers', True, True),
        ('contributors', True, True),
        ('readme', False, True),
    )


    class Meta:
        unique_together = (('backend', 'official_owner', 'slug'),)


    def __unicode__(self):
        return u'%s' % self.get_project()

    def get_new_status(self):
        """
        Return the status to be saved
        """
        default = super(Repository, self).get_new_status()
        if default != self.STATUS.ok:
            return default

        # need the parents fork's name ?
        if self.is_fork and not self.official_fork_of:
            return self.STATUS.fetch_needed

        # need the owner (or to remove it) ?
        if self.official_owner and not self.owner_id:
            return self.STATUS.need_related
        if not self.official_owner and self.owner_id:
            return self.STAUTS.need_related

        # need the parent fork ?
        if self.is_fork and not self.parent_fork_id:
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
        if not super(Repository, self).fetch():
            return False

        self.get_backend().repository_fetch(self)
        self.last_fetch = datetime.now()

        self.save()

    def save(self, *args, **kwargs):
        """
        Update the project and sortable fields
        """
        if not self.project:
            self.project = self.get_project()
        self.project_sort = Repository.objects.slugify_project(self.project)

        if self.slug:
            self.slug_sort = slugify(self.slug)

        # auto-create a Account object for owner if one
        # is needed but not exists
        if self.official_owner and not self.owner_id:
            owner = Account.objects.get_or_new(
                self.backend,
                self.official_owner
            )
            if owner.is_new():
                owner.save()
            self.owner = owner

        super(Repository, self).save(*args, **kwargs)

    def fetch_owner(self):
        """
        Create or update the repository's owner
        """
        if not self.get_backend().supports('repository_owner'):
            return False

        if not self.official_owner:
            if self.owner_id:
                self.owner = None
                self.save()
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
        if not self.get_backend().supports('repository_parent_fork'):
            return False

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
        if not self.get_backend().supports('repository_followers'):
            return False

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

        self.followers_modified = datetime.now()
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
        is_new = account.is_new()
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

    def fetch_contributors(self):
        """
        Fetch the accounts following this repository
        """
        if not self.get_backend().supports('repository_contributors'):
            return False

        # get all previous contributors
        old_contributors = dict((a.slug, a) for a in self.contributors.all())

        # get and save new followings
        contributors_list = self.get_backend().repository_contributors(self)
        new_contributors = {}
        for gaccount in contributors_list:
            account = self.add_contributor(gaccount, False)
            if account:
                new_contributors[account.slug] = account

        # remove old contributors
        removed = set(old_contributors.keys()).difference(set(new_contributors.keys()))
        for slug in removed:
            self.remove_contributor(old_contributors[slug], update_self_count=False)

        self.contributors_modified = datetime.now()
        self.update_contributors_count(save=True)

        return True

    def add_contributor(self, account, update_self_count):
        """
        Try to add the account described by `account` as contributor of
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
        if account.is_new():
            account.save()

        # add the contributor
        self.contributors.add(account)

        # update the count if we can
        if update_self_count:
            self.update_contributors_count(save=True)

        return account

    def remove_contributor(self, account, update_self_count):
        """
        Remove the given account from the ones contributing to
        the Repository
        """
        # we have something else but an account : exit
        if not isinstance(account, Account):
            return

        # remove the contributor
        self.contributors.remove(account)

        # update the count if we can
        if update_self_count:
            self.update_contributors_count(save=True)

    def update_contributors_count(self, save):
        """
        Update the saved contributors
        """
        self.contributors_count = self.contributors.count()
        if save:
            self.save()

    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        if not url_type.startswith('repository'):
            url_type = 'repository_%s' % url_type
        params = copy(kwargs)
        if 'backend' not in params:
            params['backend'] = self.backend
        if 'project' not in params:
            params['project'] = self.project
        return (url_type, (), params)

    @models.permalink
    def get_absolute_url(self):
        """
        Home page url for this Repository
        """
        return self._get_url('home')

    @models.permalink
    def get_followers_url(self):
        """
        Followers page url for this Repository
        """
        return self._get_url('followers')

    @models.permalink
    def get_contributors_url(self):
        """
        contributors page url for this Repository
        """
        return self._get_url('contributors')

    def followers_slugs(self):
        """
        Return the followers as a list of slugs
        """
        if not hasattr(self, '_followers_slugs'):
            self._followers_slugs = [f.slug for f in self.followers.all()]
        return self._followers_slugs

    def contributors_slugs(self):
        """
        Return the contributors as a list of slugs
        """
        if not hasattr(self, '_contributors_slugs'):
            self._contributors_slugs = [f.slug for f in self.contributors.all()]
        return self._contributors_slugs

    def fetch_readme(self):
        """
        Try to get a readme in the repository
        """
        if not self.get_backend().supports('repository_readme'):
            return False

        readme = self.get_backend().repository_readme(self)

        if readme is not None:
            if isinstance(readme, (list, tuple)):
                readme_type = readme[1]
                readme = readme[0]
            else:
                readme_type = 'txt'

            self.readme = readme
            self.readme_type = readme_type
            self.readme_modified = datetime.now()
            self.save()
        return True

from core.signals import *
