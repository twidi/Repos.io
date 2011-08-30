from django.db import models
from django.contrib.auth.models import User

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField

from backends import BACKENDS, get_backend
from exceptions import SaveForbiddenInBackend
from managers import AccountManager, RepositoryManager

BACKENDS_CHOICES = Choices(*BACKENDS.keys())

class SyncableModel(TimeStampedModel):
    """
    A base model usable for al objects syncable within a provider.
    TimeStampedModel add `created` and `modified` fields, auto updated
    when needed.
    """

    STATUS = Choices(
        ('creating', 'Creating'),   # just created
        ('to_update', 'To Update'), # need to be updated
        ('updating', 'Updating'),   # update running from the backend
        ('ok', 'Ok'),               # everything ok ok
    )

    # The backend from where this object come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES)

    # A status field, using STATUS
    status = StatusField(max_length=10)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """
        Init some internal values
        """
        super(SyncableModel, self).__init__(*args, **kwargs)
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
            raise SaveForbiddenInBackend('You cannot save this object in the backend')

        self.status = self.get_new_status()
        super(SyncableModel, self).save(*args, **kwargs)


class Account(SyncableModel):
    """
    Represent an account from a backend
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

    # If there is a user linked to this account
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)

    # The last access_token for authenticated requests
    access_token = models.TextField(blank=True, null=True)

    # Followers informations

    # From the backed
    official_followers_count = models.PositiveIntegerField(blank=True, null=True)
    official_following_count = models.PositiveIntegerField(blank=True, null=True)
    # List of Account object who follow this one
    followers = models.ManyToManyField('self', related_name='following')

    # The default manager
    objects = AccountManager()

    class Meta:
        unique_together = (('backend', 'slug'),)


    def get_new_status(self):
        """
        Return the status to be saved
        """
        if not self.user_id:
            return self.STATUS.to_update
        return self.STATUS.ok

    def fetch_from_backend(self):
        """
        Fetch data from the provider
        """
        self._block_save = True
        self.get_backend().user_fetch(self)
        self._block_save = False

        self.save()


class Repository(SyncableModel):
    """
    Represent a repository from a backend
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

    # Owner

    # The owner's "slug" of this project, from the backend
    official_owner = models.CharField(max_length=255, blank=True, null=True)
    # The Account object whom own this Repository
    owner = models.ForeignKey(Account, related_name='repositories', blank=True, null=True, on_delete=models.SET_NULL)

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

    # The list of followers
    followers = models.ManyToManyField(Account, related_name='following')

    # The default manager
    objects = RepositoryManager()


    class Meta:
        unique_together = (('backend', 'slug'),)

    def get_new_status(self):
        """
        Return the status to be saved
        """
        if not self.owner_id:
            return self.STATUS.to_update
        if self.is_fork and not self.parent_fork_id:
            return self.STATUS.to_update
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
        self.project = self.get_project()
        super(Repository, self).save(*args, **kwargs)
