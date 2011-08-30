from django.db import models
from django.contrib.auth.models import User

from model_utils import Choices
from model_utils.models import TimeStampedModel, StatusModel

from backends import BACKENDS, get_backend
from exceptions import SaveForbiddenInBackend

BACKENDS_CHOICES = Choices(*BACKENDS.keys())

class AccountManager(models.Manager):
    """
    Manager for the Account model
    """

    def get_for_slug(self, backend, slug):
        """
        Try to return an existing account object for this backend/slug
        If not found, return None
        """
        try:
            return self.get(backend=backend, slug=slug)
        except:
            return None

class Account(TimeStampedModel, StatusModel):
    """
    Represent an account from a backend
    """
    STATUS = Choices(
        ('creating', 'Creating'), # just created
        ('updating', 'Updating'), # updating from the backend
        ('orphan', 'Orphan'),     # updated, but without associated user
        ('ok', 'Ok'),             # everything is ok
    )


    # If there is a user linked to this account
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    # The backend from with this account come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES)
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


    def __init__(self, *args, **kwargs):
        """
        Init some internal values
        """
        super(Account, self).__init__(*args, **kwargs)
        self._block_save = False

    def fetch_from_backend(self):
        """
        Fetch data from the provider
        """
        backend = get_backend(self.backend)

        self._block_save = True
        backend.user_fetch(self)
        self._block_save = False

        self.save()

    def save(self, *args, **kwargs):
        """
        Save is forbidden while in the backend...
        """
        if self._block_save:
            raise SaveForbiddenInBackend('You cannot save this object in the backend')
        super(Account, self).save(*args, **kwargs)



class RepositoryManager(models.Manager):
    pass

class Repository(TimeStampedModel, StatusModel):
    """
    Represent a repository from a backend
    """
    STATUS = Choices(
        ('creating', 'Creating'), # just created
        ('updating', 'Updating'), # updating from the backend
        ('ok', 'Ok'),             # everything ok ok
    )

    # The backend from with this repository come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES)

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


    def __init__(self, *args, **kwargs):
        """
        Init some internal values
        """
        super(Repository, self).__init__(*args, **kwargs)
        self._block_save = False

    def get_backend(self):
        if not hasattr(self, '_backend'):
            self._backend = get_backend(self.backend)
        return self._backend

    def get_project(self):
        """
        Return the project name (sort of identifier)
        """
        if self.project:
            return self.project
        return self.get_backend().repository_project(self)

    def fetch_from_backend(self):
        """
        Fetch data from the provider
        """
        backend = get_backend(self.backend)

        self._block_save = True
        backend.repository_fetch(self)
        self._block_save = False

        self.save()

    def save(self, *args, **kwargs):
        """
        Save is forbidden while in the backend...
        """
        if self._block_save:
            raise SaveForbiddenInBackend('You cannot save this object in the backend')
        super(Repository, self).save(*args, **kwargs)
