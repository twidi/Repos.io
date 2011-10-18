from datetime import datetime, timedelta
from copy import copy
import math

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField

from core.backends import BACKENDS, get_backend
from core.managers import AccountManager, RepositoryManager, OptimForListAccountManager, OptimForListRepositoryManager
from core.core_utils import slugify
from core.exceptions import MultipleBackendError

from tagging.models import PublicTaggedAccount, PublicTaggedRepository, Tag, PrivateTaggedAccount, PrivateTaggedRepository
from tagging.words import get_tags_for_repository
from tagging.managers import TaggableManager

from private.views import get_user_note_for_object, get_user_tags_for_object

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
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES, db_index=True)

    # A status field, using STATUS
    status = StatusField(max_length=15, db_index=True)

    # Date of last own full fetch
    last_fetch = models.DateTimeField(blank=True, null=True, db_index=True)

    # Store a score for this object
    score = models.PositiveIntegerField(default=0, db_index=True)

    # object's fields

    # The slug for this object (text identifier for the provider)
    slug = models.SlugField(max_length=255, db_index=True)
    # for speed search in get_or_new
    slug_lower = models.SlugField(max_length=255, db_index=True)
    # The same, adapted for sorting
    slug_sort = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    # The fullname
    name = models.CharField(max_length=255, blank=True, null=True)
    # The web url
    url = models.URLField(max_length=255, blank=True, null=True)

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

    def get_new_status(self, for_save=False):
        """
        Return the status to be saved
        """
        # no id, object is in creating mode
        if not self.id and not for_save:
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

    def save(self, *args, **kwargs):
        """
        Save is forbidden while in the backend...
        Also update the status before saving
        """
        self.status = self.get_new_status(for_save=True)
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

    def fetch(self, token=None):
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

    def fetch_related(self, limit=None, update_related_objects=True, token=None, ignore=None):
        """
        If the object has some related content that need to be fetched, do
        it, but limit the fetch to the given limit (default 1)
        Returns the number of operations done
        """
        done = 0
        exceptions = []
        if ignore is None:
            ignore = []
        for name, with_count, with_modified in self.related_operations:
            if name in ignore:
                continue
            if not self.fetch_related_allowed_for(name):
                continue
            action = getattr(self, 'fetch_%s' % name)

            try:
                params = dict(
                    token = token
                )
                if with_count:
                    params['update_related_objects'] = update_related_objects
                if action(**params):
                    done += 1
            except Exception, e:
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
                raise MultipleBackendError([str(e) for e in exceptions])

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

    def get_user_note(self):
        """
        Return the note for the current user
        """
        return get_user_note_for_object(self)

    def get_user_tags(self):
        """
        Return the tags for the current user
        """
        return get_user_tags_for_object(self)

    def compute_score(self):
        """
        Compute the current score for the object
        """
        parts = {}
        if self.homepage:
            parts['homepage'] = 3
        if self.last_fetch:
            parts['last_fetch'] = 5

        #print parts
        return int(sum(parts.values()))

    def update_score(self, save=True):
        """
        Update the score and save it
        """
        self.score = self.compute_score()
        if save:
            self.save()

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = self.score
        if force_compute or not score:
            score = self.compute_score()
        return score/100.0


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

    # The avatar url
    avatar = models.URLField(max_length=255, blank=True, null=True)
    # The account's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # Is this account private ?
    private = models.NullBooleanField(blank=True, null=True, db_index=True)
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

    # Count of contributed projects
    contributing_count = models.PositiveIntegerField(blank=True, null=True)

    # The managers
    objects = AccountManager()
    for_list = OptimForListAccountManager()

    # tags
    public_tags = TaggableManager(through=PublicTaggedAccount, related_name='public_on_accounts')
    private_tags = TaggableManager(through=PrivateTaggedAccount, related_name='private_on_accounts')

    # Fetch operations
    backend_prefix = 'user_'
    related_operations = (
        # name, with count, with modified
        ('following', True, True),
        ('followers', True, True),
        ('repositories', True, True),
    )

    class Meta:
        unique_together = (
            ('backend', 'slug'),
            ('backend', 'slug_lower')
        )

    def fetch(self, token=None):
        """
        Fetch data from the provider
        """
        if not super(Account, self).fetch(token=token):
            return False

        self.get_backend().user_fetch(self, token=token)
        self.last_fetch = datetime.now()

        if not self.official_following_count:
            self.following_modified = self.last_fetch
            self.following_count = 0
            if self.following_count:
                for following in self.following.all():
                    self.remove_following(following, False, True)

        if not self.official_followers_count:
            self.followers_modified = self.last_fetch
            self.followers_count = 0
            if self.followers_count:
                for follower in self.followers.all():
                    self.remove_follower(follower, False, True)

        self.save()
        return True

    def save(self, *args, **kwargs):
        """
        Update the project and sortable fields
        """
        if self.slug:
            self.slug_sort = slugify(self.slug)
            self.slug_lower = self.slug.lower()
        super(Account, self).save(*args, **kwargs)

    def fetch_following(self, update_related_objects=True, token=None):
        """
        Fetch the accounts followed by this account
        """
        if not self.get_backend().supports('user_following'):
            return False

        if not self.official_following_count and (
            not self.last_fetch or self.last_fetch > datetime.now()-timedelta(hours=1)):
                return False

        # get all previous following
        check_diff = bool(self.following_count)
        if check_diff:
            old_following = dict((a.slug, a) for a in self.following.all())
            new_following = {}

        # get and save new followings
        following_list = self.get_backend().user_following(self, token=token)
        count = 0
        for gaccount in following_list:
            account = self.add_following(gaccount, False, update_related_objects)
            if account:
                count += 1
                if check_diff:
                    new_following[account.slug] = account

        # remove old following
        if check_diff:
            removed = set(old_following.keys()).difference(set(new_following.keys()))
            for slug in removed:
                self.remove_following(old_following[slug], False, update_related_objects)

        self.following_modified = datetime.now()
        self.update_following_count(save=True, use_count=count)

        return True

    def add_following(self, account, update_self_count, update_following):
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
        if update_following and not is_new:
            account.update_followers_count(save=True)

        return account

    def remove_following(self, account, update_self_count, update_following=True):
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
        if update_following:
            account.update_followers_count(save=True)

        return account

    def update_following_count(self, save, use_count=None):
        """
        Update the saved following count
        """
        self.following_count = use_count or self.following.count()
        if save:
            self.save()

    def fetch_followers(self, update_related_objects=True, token=None):
        """
        Fetch the accounts following this account
        """
        if not self.get_backend().supports('user_followers'):
            return False

        if not self.official_followers_count and (
            not self.last_fetch or self.last_fetch > datetime.now()-timedelta(hours=1)):
                return False

        # get all previous followers
        check_diff = bool(self.followers_count)
        if check_diff:
            old_followers = dict((a.slug, a) for a in self.followers.all())
            new_followers = {}

        # get and save new followings
        followers_list = self.get_backend().user_followers(self, token=token)
        count = 0
        for gaccount in followers_list:
            account = self.add_follower(gaccount, False, update_related_objects)
            if account:
                count += 1
                if check_diff:
                    new_followers[account.slug] = account

        # remove old followers
        if check_diff:
            removed = set(old_followers.keys()).difference(set(new_followers.keys()))
            for slug in removed:
                self.remove_follower(old_followers[slug], False, update_related_objects)

        self.followers_modified = datetime.now()
        self.update_followers_count(save=True, use_count=count)

        return True

    def add_follower(self, account, update_self_count, update_follower=True):
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
        if update_follower and not is_new:
            account.update_following_count(save=True)

        return account

    def remove_follower(self, account, update_self_count, update_follower=True):
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
        if update_follower:
            account.update_following_count(save=True)

    def update_followers_count(self, save, use_count=None):
        """
        Update the saved followers count
        """
        self.followers_count = use_count or self.followers.count()
        if save:
            self.save()

    def fetch_repositories(self, update_related_objects=True, token=None):
        """
        Fetch the repositories owned/watched by this account
        """
        if not self.get_backend().supports('user_repositories'):
            return False

        # get all previous repositories
        check_diff = bool(self.repositories_count)
        if check_diff:
            old_repositories = dict((r.project, r) for r in self.repositories.all())
            new_repositories = {}

        # get and save new repositories
        repositories_list = self.get_backend().user_repositories(self, token=token)
        count = 0
        for grepo in repositories_list:
            repository = self.add_repository(grepo, False, update_related_objects)
            if repository:
                count += 1
                if check_diff:
                    new_repositories[repository.project] = repository

        # remove old repositories
        if check_diff:
            removed = set(old_repositories.keys()).difference(set(new_repositories.keys()))
            for project in removed:
                self.remove_repository(old_repositories[project], False, update_related_objects)

        self.repositories_modified = datetime.now()
        self.update_repositories_count(save=True, use_count=count)

        return True

    def add_repository(self, repository, update_self_count, update_repository=True):
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
        if update_repository and not is_new:
            repository.update_followers_count(save=True)

        return repository

    def remove_repository(self, repository, update_self_count, update_repository=True):
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
        if update_repository:
            repository.update_followers_count(save=True)

    def update_repositories_count(self, save, use_count=None):
        """
        Update the saved repositories count
        """
        self.repositories_count = use_count or self.repositories.count()
        if save:
            self.save()

    def update_contributing_count(self, save, use_count=None):
        """
        Update the contributed repositories count
        """
        self.contributing_count = use_count or self.contributing.count()
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

    @models.permalink
    def get_contributing_url(self):
        """
        Contributing page url for this Account
        """
        return self._get_url('contributing')

    def following_ids(self):
        """
        Return the following as a list of ids
        """
        if not hasattr(self, '_following_ids'):
            self._following_ids = self.following.values_list('id', flat=True)
        return self._following_ids

    def followers_ids(self):
        """
        Return the followers as a list of ids
        """
        if not hasattr(self, '_followers_ids'):
            self._followers_ids = self.followers.values_list('id', flat=True)
        return self._followers_ids

    def compute_score(self):
        """
        Compute the current score for this account
        """
        score = super(Account, self).compute_score()

        parts = {}
        # basic scores
        if self.name != self.slug:
            parts['name'] = 3
        if self.user_id:
            parts['user'] = 5
        if self.official_created:
            parts['life_time'] = ((datetime.now() - self.official_created).days) / 40.0
        # popularity
        if self.official_followers_count or self.followers_count:
            parts['followers'] = min(max(self.official_followers_count, self.followers_count) / 5.0, 100)
        # contents
        if self.repositories_count:
            all_repositories = self.own_repositories.all()
            nb_own = all_repositories.count()
            nb_forks = all_repositories.filter(is_fork=True).count()
            nb_real_own = nb_own - nb_forks
            parts['repositories'] = (nb_real_own + nb_forks / 2.0) / 3.0

            # popularity of its repositories
            parts['repositories_score'] = 0
            for repository in all_repositories:
                parts['repositories_score'] += repository.compute_popularity()
            parts['repositories_score'] = min(parts['repositories_score'] / 10.0, 100)
        if self.contributing_count:
            parts['contributing'] = self.contributing_count / 20.0

        #print parts
        score += sum(parts.values())
        return int(round(score))

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = super(Account, self).score_to_boost(force_compute=force_compute)
        return math.log10(max(score*100, 5) / 2.0) - 0.3

    def find_public_tags(self):
        """
        Update the public tags for this accounts.
        """
        tags = {}
        rep_tagged_items = PublicTaggedRepository.objects.filter(content_object__followers=self).select_related('content_object', 'tag')
        for tagged_item in rep_tagged_items:
            repository = tagged_item.content_object
            divider = 1.0
            if repository.is_fork:
                divider = 2
            if repository.owner_id != self.id:
                divider = divider * 3
            if tagged_item.tag.slug not in tags:
                tags[tagged_item.tag.slug] = 0
            tags[tagged_item.tag.slug] += (tagged_item.weight or 1) / divider

        tags = sorted(tags.iteritems(), key=lambda t: t[1], reverse=True)

        self.public_tags.set(tags[:5])

    def all_public_tags(self, with_weight=False):
        """
        Return all public tags for this account.
        Use this instead of self.public_tags.all() because
        we set the default order
        If `with_weight` is True, return the through model of the tagging
        system, with tags and weight.
        Else simply returns tags.
        in both cases, sort is by weight (desc) and slug (asc)
        """
        if with_weight:
            qs = self.publictaggedaccount_set.select_related('tag').all()
        else:
            qs = self.public_tags.order_by('-public_account_tags__weight', 'slug')

        return qs

    def all_private_tags(self, user):
        """
        Return all private tags for this account set by the given user.
        Use this instead of self.private_tags.filter(owner=user) because
        we set the default order
        """
        return self.private_tags.filter(private_account_tags__owner=user).order_by('-private_account_tags__weight', 'slug').distinct()

    def links_with_user(self, user):
        """
        Return informations about some links between this account and the given user
        """
        backend = self.get_backend()
        links = {}

        if self.user_id == user.id:
            links['self'] = self.user

        if backend.supports('user_following'):
            followed = self.following.filter(user=user)
            if followed:
                links['followed'] = followed

        if backend.supports('user_followers'):
            following = self.followers.filter(user=user)
            if following:
                links['following'] = following

        if backend.supports('repository_followers'):
            project_following = Repository.objects.filter(owner=self, followers__user=user)
            if project_following:
                links['project_following'] = project_following
            project_followed = Repository.objects.filter(owner__user=user, followers=self)
            if project_followed:
                links['project_followed'] = project_followed

        return links

    def get_default_token(self):
        """
        Return the token object for this account
        """
        return self.get_backend().token_manager().get_for_account(self)


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

    # The description of this repository
    description = models.TextField(blank=True, null=True)
    # The project's logo url
    logo = models.URLField(max_length=255, blank=True, null=True)
    # The project's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # The canonical project name (example twidi/myproject)
    project = models.TextField(db_index=True)
    # The same, adapted for sorting
    project_sort = models.TextField(db_index=True)
    # Is this repository private ?
    private = models.NullBooleanField(blank=True, null=True, db_index=True)
    # Repository dates
    official_created = models.DateTimeField(blank=True, null=True)
    official_modified = models.DateTimeField(blank=True, null=True)

    # Owner

    # The owner's "slug" of this project, from the backend
    official_owner = models.CharField(max_length=255, blank=True, null=True)
    # for speed search in get_or_new
    official_owner_lower = models.CharField(max_length=255, blank=True, null=True)
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

    # The managers
    objects = RepositoryManager()
    for_list = OptimForListRepositoryManager()

    # tags
    public_tags = TaggableManager(through=PublicTaggedRepository, related_name='public_on_repositories')
    private_tags = TaggableManager(through=PrivateTaggedRepository, related_name='private_on_repositories')

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


    def __unicode__(self):
        return u'%s' % self.get_project()

    def get_new_status(self, for_save=False):
        """
        Return the status to be saved
        """
        default = super(Repository, self).get_new_status(for_save=for_save)
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

    def fetch(self, token=None):
        """
        Fetch data from the provider
        """
        if not super(Repository, self).fetch(token=token):
            return False

        self.get_backend().repository_fetch(self, token=token)
        self.last_fetch = datetime.now()

        if not self.official_followers_count:
            self.followers_modified = self.last_fetch
            self.followers_count = 0
            if self.followers_count:
                for follower in self.followers.all():
                    self.remove_follower(follower, False, True)

        if not self.modified:
            self.readme_modified = self.last_fetch

        self.save()

        return True

    def save(self, *args, **kwargs):
        """
        Update the project and sortable fields
        """
        if not self.project:
            self.project = self.get_project()
        self.project_sort = Repository.objects.slugify_project(self.project)

        if self.slug:
            self.slug_sort = slugify(self.slug)
            self.slug_lower = self.slug.lower()

        if self.official_owner:
            self.official_owner_lower = self.official_owner.lower()
            # auto-create a Account object for owner if one is needed but not exists
            if not self.owner_id:
                owner = Account.objects.get_or_new(
                    self.backend,
                    self.official_owner
                )
                if owner.is_new():
                    owner.save()
                self.owner = owner

        super(Repository, self).save(*args, **kwargs)

    def fetch_owner(self, token=None):
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
            owner.fetch(token=token)
            fetched = True

        if save_needed:
            if not self.owner_id:
                self.owner = owner
            self.add_follower(owner, True, True)

        return fetched

    def fetch_parent_fork(self, token=None):
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
            parent_fork.fetch(token=token)
            fetched = True

        if save_needed:
            if not self.parent_fork_id:
                self.parent_fork = parent_fork
            self.save()

        return fetched

    def fetch_followers(self, update_related_objects=True, token=None):
        """
        Fetch the accounts following this repository
        """
        if not self.get_backend().supports('repository_followers'):
            return False

        if not self.official_followers_count and (
            not self.last_fetch or self.last_fetch > datetime.now()-timedelta(hours=1)):
                return False

        # get all previous followers
        check_diff = bool(self.followers_count)
        if check_diff:
            old_followers = dict((a.slug, a) for a in self.followers.all())
            new_followers = {}

        # get and save new followings
        followers_list = self.get_backend().repository_followers(self, token=token)
        count = 0
        for gaccount in followers_list:
            account = self.add_follower(gaccount, False, update_related_objects)
            if account:
                count += 1
                if check_diff:
                    new_followers[account.slug] = account

        # remove old followers
        if check_diff:
            removed = set(old_followers.keys()).difference(set(new_followers.keys()))
            for slug in removed:
                self.remove_follower(old_followers[slug], False, update_related_objects)

        self.followers_modified = datetime.now()
        self.update_followers_count(save=True, use_count=count)

        return True

    def add_follower(self, account, update_self_count, update_follower=True):
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
        if update_follower and not is_new:
            account.update_repositories_count(save=True)

        return account

    def remove_follower(self, account, update_self_count, update_follower=True):
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

        # update the followers count for the other account
        if update_follower:
            account.update_repositories_count(save=True)

    def update_followers_count(self, save, use_count=None):
        """
        Update the saved followers
        """
        self.followers_count = use_count or self.followers.count()
        if save:
            self.save()

    def fetch_contributors(self, update_related_objects=True, token=None):
        """
        Fetch the accounts following this repository
        """
        if not self.get_backend().supports('repository_contributors'):
            return False

        # get all previous contributors
        check_diff = bool(self.contributors_count)
        if check_diff:
            old_contributors = dict((a.slug, a) for a in self.contributors.all())
            new_contributors = {}

        # get and save new followings
        contributors_list = self.get_backend().repository_contributors(self, token=token)
        count = 0
        for gaccount in contributors_list:
            account = self.add_contributor(gaccount, False, update_related_objects)
            if account:
                count += 1
                if check_diff:
                    new_contributors[account.slug] = account

        # remove old contributors
        if check_diff:
            removed = set(old_contributors.keys()).difference(set(new_contributors.keys()))
            for slug in removed:
                self.remove_contributor(old_contributors[slug], False, update_related_objects)

        self.contributors_modified = datetime.now()
        self.update_contributors_count(save=True, use_count=count)

        return True

    def add_contributor(self, account, update_self_count, update_contributor=True):
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
        is_new = account.is_new()
        if is_new:
            account.contributing_count = 1
            account.save()

        # add the contributor
        self.contributors.add(account)

        # update the count if we can
        if update_self_count:
            self.update_contributors_count(save=True)

        # update the repositories count for the account
        if update_contributor and not is_new:
            account.update_contributing_count(save=True)

        return account

    def remove_contributor(self, account, update_self_count, update_contributor=True):
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

        # update the contributing count for the other account
        if update_contributor:
            account.update_contributing_count(save=True)

    def update_contributors_count(self, save, use_count=None):
        """
        Update the saved contributors
        """
        self.contributors_count = use_count or self.contributors.count()
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

    def followers_ids(self):
        """
        Return the followers as a list of ids
        """
        if not hasattr(self, '_followers_ids'):
            self._followers_ids = self.followers.values_list('id', flat=True)
        return self._followers_ids

    def contributors_ids(self):
        """
        Return the contributors as a list of ids
        """
        if not hasattr(self, '_contributors_ids'):
            self._contributors_ids = self.contributors.values_list('id', flat=True)
        return self._contributors_ids

    def fetch_readme(self, token=None):
        """
        Try to get a readme in the repository
        """
        if not self.get_backend().supports('repository_readme'):
            return False

        readme = self.get_backend().repository_readme(self, token=token)

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

    def compute_popularity(self):
        """
        Compute the popularity of the repository, used to compute it's total
        score, and also to compute it's owner's score
        """
        parts = {}

        if self.official_followers_count or self.followers_count:
            parts['followers'] = max(self.official_followers_count, self.followers_count) / 10.0

        if self.official_forks_count:
            parts['forks'] = self.official_forks_count / 5.0

        if self.official_modified:
            parts['life_time'] = ((self.official_modified - self.official_created).days) / 10.0
            parts['zombie'] = ((datetime.now() - self.official_modified).days) / -20.0
            if parts['zombie'] + parts['life_time'] < 0:
                del parts['life_time']
                del parts['zombie']
        else:
            parts['born_dead'] = -20

        #print self.project, parts
        score = sum(parts.values())
        if self.is_fork:
            score = score / 1.5

        return min(score, 200)

    def compute_score(self):
        """
        Compute the current score for this repository
        """
        score = super(Repository, self).compute_score()
        parts = {}
        # basic scores
        divider = 1
        if self.is_fork:
            divider = 2.0
        if self.description:
            parts['description'] = 5 / divider
        if self.readme:
            parts['readme'] = 5 / divider
        if self.owner_id:
            parts['owner'] = (self.owner.score or self.owner.compute_score()) / 20.0 / divider

        parts['popularity'] = self.compute_popularity()

        #print parts
        score += sum(parts.values())
        return int(round(score))

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = super(Repository, self).score_to_boost(force_compute=force_compute)
        return math.log1p(max(score*100, 5) / 5.0) - 0.6

    def find_public_tags(self, known_tags=None):
        """
        Update the public tags for this repository.
        """
        if not known_tags:
            known_tags = set(Tag.objects.filter(official=True).values_list('slug', flat=True))
        rep_tags = get_tags_for_repository(self, known_tags)
        tags = sorted(rep_tags.iteritems(), key=lambda t: t[1], reverse=True)
        self.public_tags.set(tags[:5])

    def all_public_tags(self, with_weight=False):
        """
        Return all public tags for this repository.
        Use this instead of self.public_tags.all() because
        we set the default order
        If `with_weight` is True, return the through model of the tagging
        system, with tags and weight.
        Else simply returns tags.
        in both cases, sort is by weight (desc) and slug (asc)
        """
        if with_weight:
            qs = self.publictaggedrepository_set.select_related('tag').all()
        else:
            qs = self.public_tags.order_by('-public_repository_tags__weight', 'slug')
        return qs

    def all_private_tags(self, user):
        """
        Return all private tags for this repository set by the given user.
        Use this instead of self.private_tags.filter(owner=user) because
        we set the default order
        """
        return self.private_tags.filter(private_repository_tags__owner=user).order_by('-private_repository_tags__weight', 'slug').distinct()

    def links_with_user(self, user):
        """
        Return informations about some links between this repository and the given user
        """
        backend = self.get_backend()
        links = {}

        if backend.supports('repository_owner'):
            if self.owner.user_id == user.id:
                links['owning'] = self.owner

            if backend.supports('repository_parent_fork'):
                forks = self.forks.filter(owner__user=user)
                if forks:
                    links['forks'] = forks

                project_forks = Repository.objects.filter(
                        slug_lower=self.slug_lower, owner__user=user).select_related('owner').exclude(
                                id=self.id)
                if forks:
                    project_forks = project_forks.exclude(id__in=list(fork.id for fork in forks))
                if project_forks:
                    links['project_forks'] = project_forks

        if backend.supports('repository_followers'):
            following = self.followers.filter(user=user)
            if following:
                links['following'] = following

            project_following = Repository.objects.filter(
                    slug_lower=self.slug_lower, followers__user=user).exclude(
                            owner__user=user).exclude(id=self.id).select_related('owner')
            if project_following:
                links['project_following'] = project_following

        if backend.supports('repository_contributors'):
            contributing = self.contributors.filter(user=user)
            if contributing:
                links['contributing'] = contributing

        return links

    def get_default_token(self):
        """
        Return the token object for this repository's owner
        """
        if self.owner_id:
            return self.get_backend().token_manager().get_for_account(self.owner)
        return None


from core.signals import *
