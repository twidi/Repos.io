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
        if self.status == 'ok' and self.modified < datetime.now() - MIN_FETCH_DELTA:
            return True
        return False

    def fetch_related_needed(self):
        """
        Check if we need to update some related objects
        """
        return bool(self.id) and self.status == self.STATUS.need_related

    def fetch_related(self, limit=1):
        """
        If the object has some related content that need to be fetched, do
        it, but limit the fetch to the given limit (default 1)
        Returns the number of operations done
        """
        done = 0
        for operation_name in self.fetch_related_operations:
            operation = getattr(self, 'fetch_%s' % operation_name)
            if operation():
                done += 1
            if limit and done >= limit:
                return
        return done

    def update_related(self, limit=None):
        """
        Update one or many (default all) related objects
        """
        if not self.fetch_related_needed():
            return
        if self.fetch_related(limit):
            self.save()


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
    # List of followed Account object
    following = models.ManyToManyField('self', related_name='followers')

    # List of owned/watched repositories
    repositories = models.ManyToManyField('Repository', related_name='accounts')
    # Saved count
    repositories_count = models.PositiveIntegerField(blank=True, null=True)

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
        if not self.user_id:
            return self.STATUS.to_update
        if None in (self.following_count, self.followers_count, self.repositories_count):
            return self.STATUS.need_related
        return self.STATUS.ok

    def fetch_from_backend(self):
        """
        Fetch data from the provider
        """
        self._block_save = True
        self.get_backend().user_fetch(self)
        self._block_save = False

        self.save()

    def fetch_related_needed(self):
        """
        Do net fetch related if we have no user
        """
        if not self.user_id:
            return False
        return super(Account, self).fetch_related_needed()

    def fetch_following(self):
        """
        Fetch the accounts followed by this account
        """
        if not self.user_id:
            return False

    def fetch_followers(self):
        """
        Fetch the accounts following this account
        """
        if not self.user_id:
            return False

    def fetch_repositories(self):
        """
        Fetch the repositories owned/watched by this account
        """
        if not self.user_id:
            return False


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

    # Set to True if this Repository is a fork of another
    is_fork = models.NullBooleanField(blank=True, null=True)
    # The Repository object from which this repo is the fork
    parent_fork = models.ForeignKey('self', related_name='forks', blank=True, null=True, on_delete=models.SET_NULL)

    # The default manager
    objects = RepositoryManager()

    # Fetch operations
    fetch_related_operations = ('owner', 'parent_fork', )


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
        # need the owner ?
        if not self.owner_id:
            return self.STATUS.need_related
        # need the parent fork ?
        if self.is_fork and not self.parent_fork_id:
            return self.STATUS.need_related
        return self.STATUS.ok

    def get_project(self):
        """
        Return the project name (sort of identifier)
        """
        return self.project or self.get_backend().repository_project(self)

    def fetch_from_backend(self):
        """
        Fetch data from the provider
        """
        self._block_save = True
        self.get_backend().repository_fetch(self)
        self._block_save = False

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
        save_needed = False
        fetched = False

        if not self.owner_id and not self.owner:
            save_needed = True
            owner = Account.objects.get_or_new(self.backend, self.official_owner)
        else:
            owner = self.owner

        if owner.fetch_needed():
            owner.fetch_from_backend()
            fetched = True

        if save_needed:
            if not self.owner_id:
                self.owner = owner
            self.save()
            self.accounts.add(self.owner)

        return fetched

    def fetch_parent_fork(self):
        """
        Create of update the parent fork, only if needed and if we have the
        parent fork's name
        """
        if not (self.is_fork and self.official_fork_of):
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
            parent_fork.fetch_from_backend()
            fetched = True

        if save_needed:
            if not self.parent_fork_id:
                self.parent_fork = parent_fork
            self.save()

        return fetched
