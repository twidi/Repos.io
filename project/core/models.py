# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from datetime import datetime, timedelta
from copy import copy
import math
import sys
import traceback

from django.db import models, transaction, IntegrityError, DatabaseError
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import simplejson
from django.core.cache import cache
from django.template import loader, Context
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from django.contrib.contenttypes.generic import GenericRelation

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField
from haystack import site
from redisco.containers import List, Set, Hash, SortedSet

from core import REDIS_KEYS
from core.backends import BACKENDS, get_backend
from core.managers import (AccountManager, RepositoryManager,
                           OptimForListAccountManager, OptimForListRepositoryManager,
                           OptimForListWithoutDeletedAccountManager, OptimForListWithoutDeletedRepositoryManager)
from core.core_utils import slugify
from core.exceptions import BackendError, BackendNotFoundError, BackendSuspendedTokenError, MultipleBackendError
from core import messages as offline_messages

from tagging.models import PublicTaggedAccount, PublicTaggedRepository, PrivateTaggedAccount, PrivateTaggedRepository, all_official_tags
from tagging.words import get_tags_for_repository
from tagging.managers import TaggableManager
from notes.models import Note

from utils.model_utils import get_app_and_model, update as model_update
from utils import now_timestamp, dt2timestamp

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
    # limit for auto fetch full
    MIN_FETCH_FULL_DELTA = getattr(settings, 'MIN_FETCH_FULL_DELTA', timedelta(days=2))

    # The backend from where this object come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES, db_index=True)

    # A status field, using STATUS
    status = StatusField(max_length=15, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)

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
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    # The web url
    url = models.URLField(max_length=255, blank=True, null=True)

    # backend errors
    backend_last_status = models.PositiveIntegerField(default=200)
    backend_same_status = models.PositiveIntegerField(default=0)
    backend_last_message = models.TextField(blank=True, null=True)

    note = GenericRelation(Note)

    # Fetch operations
    backend_prefix = ''
    related_operations = (
        # name, with count, with modified
    )

    class Meta:
        abstract = True

    @transaction.commit_manually
    def update(self, **kwargs):
        """
        Make an atomic update on the database, and fail gracefully
        """
        raise_if_error = kwargs.pop('raise_if_error', True)
        try:
            model_update(self, **kwargs)
        except (DatabaseError, IntegrityError), e:
            sys.stderr.write('\nError when updating %s with : %s\n' % (self, kwargs))
            sys.stderr.write(' => %s\n' % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())) + '\n')
            sys.stderr.write("====================================================================\n")
            transaction.rollback()
            if raise_if_error:
                raise e
        except:
            transaction.commit()
        else:
            transaction.commit()

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
        if not self.last_fetch or self.last_fetch < datetime.utcnow() - self.MIN_FETCH_DELTA_NEEDED:
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
                if not date or date < datetime.utcnow() - self.MIN_FETCH_RELATED_DELTA_NEEDED:
                    return self.STATUS.need_related

        # else, default ok
        return self.STATUS.ok

    def save(self, *args, **kwargs):
        """
        Update the status before saving, and update some stuff (score, search index, tags)
        """
        self.status = self.get_new_status(for_save=True)
        super(SyncableModel, self).save(*args, **kwargs)
        self.update_related_data(async=True)

    def update_related_data(self, async=False):
        """
        Update data related to this object, as score,
        search index, public tags
        """
        if async:
            self_str = self.simple_str()
            to_update_set = Set(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY)
            if self_str not in to_update_set:
                to_update_set.add(self_str)
                List(settings.WORKER_UPDATE_RELATED_DATA_KEY).append(self_str)
            return

        self.update_score()
        self.update_search_index()
        self.find_public_tags()

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
        if self.deleted:
            return False
        return bool(not self.last_fetch or self.last_fetch < datetime.utcnow() - self.MIN_FETCH_DELTA)

    def fetch(self, token=None, log_stderr=False):
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
        if self.deleted:
            return False
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
        if not date or date < datetime.utcnow() - self.MIN_FETCH_RELATED_DELTA:
            return True

        return False

    def fetch_related(self, limit=None, token=None, ignore=None, log_stderr=False):
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

            if log_stderr:
                sys.stderr.write("      - %s\n" % name)

            try:
                if action(token=token):
                    done += 1
            except Exception, e:
                if log_stderr:
                    sys.stderr.write("          => ERROR : %s\n" % e)
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
                raise MultipleBackendError(exceptions)

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

    def get_user_note(self, user=None):
        """
        Return the note for the current (or given) user
        """
        from private.views import get_user_note_for_object
        return get_user_note_for_object(self, user)

    def get_user_tags(self, user=None):
        """
        Return the tags for the current (or given) user
        """
        from private.views import get_user_tags_for_object
        return get_user_tags_for_object(self, user)

    def _compute_score_part(self, value):
        """
        Apply a mathematical operation to a value and return the result to
        be used as a part of a score
        """
        return math.sqrt(value)

    def _compute_final_score(self, parts, divider):
        """
        Take many parts of the score, a divider, and return a final score
        """
        score = sum(parts.values())/divider * 10
        if score > 0:
            return score * math.log1p(score) / 10
        else:
            return 0

    def prepare_score(self):
        """
        Prepare the computation of current score for this object
        """
        parts = dict(infos=0.0)
        divider = 0.0

        if self.name != self.slug:
            parts['infos'] += 0.3
        if self.homepage:
            parts['infos'] += 0.3
        if self.last_fetch:
            parts['infos'] += 0.3

        return parts, divider

    def compute_score(self):
        """
        Compute the final score of this object
        """
        parts, divider = self.prepare_score()
        return self._compute_final_score(parts, divider)

    def update_score(self, save=True):
        """
        Update the score and save it
        """
        if self.deleted:
            return

        self.score = int(round(self.compute_score()))
        if save:
            self.update(score=self.score)
        if self.score > 100:
            SortedSet(self.get_redis_key('best_scored')).add(self.id, self.score)

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = self.score
        if force_compute or not score:
            score = self.compute_score()
        return score/100.0

    def simple_str(self):
        """
        Return a unique string for this object, usable as a key (in redis or...)
        """
        return '%s:%d' % ('.'.join(get_app_and_model(self)), self.pk)

    def get_last_full_fetched(self):
        """
        Return the timestamp of the last fetch
        """
        return SortedSet(self.get_redis_key('last_fetched')).score(self.id)

    def fetch_full_allowed(self, delta=None):
        """
        Return True if a fetch_full can be done, respecting a delay
        """
        if delta is None:
            delta = self.MIN_FETCH_FULL_DELTA
        score = self.get_last_full_fetched()
        return not score or score < dt2timestamp(datetime.utcnow() - delta)

    def should_stop_use_token(self, fetch_error):
        return fetch_error and (getattr(fetch_error, 'code', None) == 401
                                or isinstance(fetch_error, BackendSuspendedTokenError))

    def fetch_full(self, token=None, depth=0, async=False, async_priority=None,
                   notify_user=None, allowed_interval=None):
        """
        Make a full fetch of the current object : fetch object and related
        """

        # check if not done too recently
        if not self.fetch_full_allowed(allowed_interval):
            return token, None

        # init
        self_str = self.simple_str()
        redis_hash = Hash(settings.WORKER_FETCH_FULL_HASH_KEY)

        # manage async mode
        if async:
            if async_priority is None:
                async_priority = depth


            # check if already in a better priority list
            try:
                existing_priority = int(redis_hash[self_str])
            except:
                existing_priority = None
            if existing_priority is not None and existing_priority >= async_priority:
                return token, None

            sys.stderr.write("SET ASYNC (%d) FOR FETCH FULL %s #%d (token=%s)\n" % (depth, self, self.pk, token))

            # async : we serialize the params and put them into redis for future use
            data = dict(
                object = self_str,
                token = token.uid if token else None,
                depth = depth,
            )
            if notify_user:
                data['notify_user'] = notify_user.id if isinstance(notify_user, User) else notify_user

            # add the serialized data to redis
            data_s = simplejson.dumps(data)
            redis_hash[self_str] = async_priority
            List(settings.WORKER_FETCH_FULL_KEY % async_priority).append(data_s)

            # return dummy data when asyc
            return token, None

        else:
            del redis_hash[self_str]

        # ok, GO
        dmain = datetime.utcnow()
        fetch_error = None
        try:

            backend = self.get_backend()
            token_manager = backend.token_manager()

            token = token_manager.get_one(token)

            sys.stderr.write("FETCH FULL %s #%d (depth=%d, token=%s)\n" % (self, self.pk, depth, token))

            # start try to update the object
            try:
                df = datetime.utcnow()
                sys.stderr.write("  - fetch object (%s)\n" % self)
                fetched = self.fetch(token=token, log_stderr=True)
            except Exception, e:

                if isinstance(e, BackendSuspendedTokenError):
                    token.suspend(e.extra.get('suspended_until'), str(e))
                elif isinstance(e, BackendError) and e.code:
                    if e.code == 401:
                        token.set_status(e.code, str(e))
                    elif e.code in (403, 404):
                        self.set_backend_status(e.code, str(e))

                fetch_error = e
                ddf = datetime.utcnow() - df
                sys.stderr.write("      => ERROR (in %s) : %s\n" % (ddf, e))
                if notify_user:
                    offline_messages.error(notify_user, '%s couldn\'t be fetched' % self.str_for_user(notify_user).capitalize(), content_object=self, meta=dict(error = fetch_error))
            else:
                self.set_backend_status(200, 'ok')
                ddf = datetime.utcnow() - df
                sys.stderr.write("      => OK (%s) in %s [%s]\n" % (fetched, ddf, self.fetch_full_self_message()))

                # then fetch related
                try:
                    dr = datetime.utcnow()
                    sys.stderr.write("  - fetch related (%s)\n" % self)
                    nb_fetched = self.fetch_related(token=token, log_stderr=True)
                except Exception, e:

                    exceptions = [e]
                    if isinstance(e, MultipleBackendError):
                        exceptions = e.exceptions

                    for ex in exceptions:
                        if isinstance(ex, BackendSuspendedTokenError):
                            token.suspend(ex.extra.get('suspended_until'), str(ex))
                        elif isinstance(ex, BackendError) and ex.code:
                            if ex.code == 401:
                                token.set_status(ex.code, str(ex))
                            elif ex.code in (403, 404):
                                self.set_backend_status(ex.code, str(ex))

                    ddr = datetime.utcnow() - dr
                    sys.stderr.write("      => ERROR (in %s): %s\n" % (ddr, e))
                    fetch_error = e
                    if notify_user:
                        offline_messages.error(notify_user, 'The related of %s couldn\'t be fetched' % self.str_for_user(notify_user), content_object=self, meta=dict(error = fetch_error))
                else:
                    ddr = datetime.utcnow() - dr
                    sys.stderr.write("      => OK (%s) in %s [%s]\n" % (nb_fetched, ddr, self.fetch_full_related_message()))

            if notify_user and not fetch_error:
                offline_messages.success(notify_user, '%s was correctly fetched' % self.str_for_user(notify_user).capitalize(), content_object=self)

            # finally, perform a fetch full of related
            if not fetch_error and depth > 0:
                self.fetch_full_specific(token=token, depth=depth, async=True)

            # save the date of last fetch
            SortedSet(self.get_redis_key('last_fetched')).add(self.id, now_timestamp())

        except Exception, e:
                fetch_error = e
                sys.stderr.write("      => MAIN ERROR FOR FETCH FULL OF %s: %s (see below)\n" % (self, e))
                sys.stderr.write("====================================================================\n")
                sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
                sys.stderr.write("====================================================================\n")

        finally:
            ddmain = datetime.utcnow() - dmain
            sys.stderr.write("END OF FETCH FULL %s in %s (depth=%d)\n" % (self, ddmain, depth))

            if token:
                token.release()

            return token, fetch_error

    def str_for_user(self, user):
        """
        Given a user, try to give a personified str for this object
        """
        return 'the %s "%s"' % (self.model_name, self)


    def set_backend_status(self, code, message, save=True):
        """
        Save informations about last status
        If the status is the same than the last one, keep the count
        by incrementing the value.
        """
        if code == self.backend_last_status:
            self.backend_same_status += 1
        else:
            self.backend_same_status = 1
        self.backend_last_status = code
        self.backend_last_message = message
        if save:
            self.save()

    def update_search_index(self, search_index=None):
        """
        Update the search index for the current object
        """
        if self.deleted:
            return

        try:
            if not search_index:
                search_index = self.get_search_index()
            search_index.backend.update(search_index, [self], commit=False)
        except Exception, e:
            sys.stderr.write('ERROR in update_search_index for %s : %s' % (self.simple_str(), e))

    def remove_from_search_index(self):
        """
        Remove the current object from the search index
        """
        try:
            self.get_search_index().backend.remove(self, commit=False)
        except:
            pass

    def update_count(self, name, save=True, async=False):

        """
        Update a saved count
        """
        if async:
            # async : we serialize the params and put them into redis for future use
            data = dict(
                object = self.simple_str(),
                count_type = name,
            )
            # add the serialized data to redis
            data_s = simplejson.dumps(data)
            List(settings.WORKER_UPDATE_COUNT_KEY).append(data_s)
            return

        field = '%s_count' % name
        count = getattr(self, name).count()
        if save:
            self.update(**{field: count})
        else:
            setattr(self, field, count)

    def fetch_related_entries(self, functionality, entry_name, entries_name, key, token=None):
        """
        Fech entries of type `entries_name` from the backend by calling the `functionality` method after
        testing its support.
        The `entry_name` is used for the needed add_%s and remove_%s methods
        """
        if not self.get_backend().supports(functionality):
            return False

        official_count_field = 'official_%s_count' % entries_name
        if hasattr(self, official_count_field) and not getattr(self, official_count_field) and (
            not self.last_fetch or self.last_fetch > datetime.utcnow()-timedelta(hours=1)):
                return False

        method_add_entry = getattr(self, 'add_%s' % entry_name)
        method_rem_entry = getattr(self, 'remove_%s' % entry_name)

        # get all previous entries
        check_diff = bool(getattr(self, '%s_count' % entries_name))
        if check_diff:
            old_entries = dict((getattr(obj, key), obj) for obj in getattr(self, entries_name).all())
            new_entries = set()

        # get and save new entries
        entries_list = getattr(self.get_backend(), functionality)(self, token=token)
        for gobj in entries_list:
            if check_diff and gobj[key] in old_entries:
                if check_diff:
                    new_entries.add(gobj[key])
            else:
                obj = method_add_entry(gobj, False)
                if obj:
                    if check_diff:
                        new_entries.add(getattr(obj, key))

        # remove old entries
        if check_diff:
            removed = set(old_entries.keys()).difference(new_entries)
            for key_ in removed:
                method_rem_entry(old_entries[key_], False)

        setattr(self, '%s_modified' % entries_name, datetime.utcnow())
        self.update_count(entries_name, async=True)

        return True

    def add_related_account_entry(self, account, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `add_related_entry` with `repository` as `obj`.
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

        return self.add_related_entry(account, self_entries_name, reverse_entries_name, update_self_count)

    def add_related_repository_entry(self, repository, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `add_related_entry` with `repository` as `obj`.
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

        return self.add_related_entry(repository, self_entries_name, reverse_entries_name, update_self_count)

    def add_related_entry(self, obj, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Try to add the `obj` in the `self_entries_name` list of the current object.
        `reverse_entries_name` is the name of the obj's list to put the current
        object in (reverse list)
        `obj` must be an object of the good type (Account or Repository). It's
        recommended to call add_related_account_entry and add_related_repository_entry
        instead of this method.
        """
        # save the object if it's a new one

        to_save = is_new = obj.is_new()
        if not is_new and obj.deleted:
            obj.deleted = False
            to_save = True

        if to_save:
            setattr(obj, '%s_count' % reverse_entries_name, 1)
            obj.save()

        # add the entry
        getattr(self, self_entries_name).add(obj)

        # update the count if we can
        if update_self_count:
            self.update_count(self_entries_name, async=True)

        # update the reverse count for the other object
        if not is_new:
            obj.update_count(reverse_entries_name, async=True)

        return obj

    def remove_related_account_entry(self, account, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `remove_related_entry` with `account` as `obj`.
        `account` must be an Account instance
        """
        # we have something else but an account : exit
        if not isinstance(account, Account):
            return

        return self.remove_related_entry(account, self_entries_name, reverse_entries_name, update_self_count)

    def remove_related_repository_entry(self, repository, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `remove_related_entry` with `repository` as `obj`.
        `repository` must be an Repository instance
        """
        # we have something else but a repository : exit
        if not isinstance(repository, Repository):
            return None

        return self.remove_related_entry(repository, self_entries_name, reverse_entries_name, update_self_count)

    def remove_related_entry(self, obj, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Remove the given object from the ones in the `self_entries_name` of the
        current object.
        `reverse_entries_name` is the name of the obj's list to remove the current
        object from (reverse list)
        `obj` must be an object of the good type (Account or Repository). It's
        recommended to call remove_related_account_entry and
        remove_related_repository_entry instead of this method.
        """
        # remove from the list
        getattr(self, self_entries_name).remove(obj)

        # update the count if we can
        if update_self_count:
            self.update_count(self_entries_name, async=True)

        # update the reverse count for the other object
        obj.update_count(reverse_entries_name, async=True)

        return obj

    def fake_delete(self, to_update):
        """
        Set the object as deleted and update all given field (*_count and
        *_modified, set to 0 and now() by subclasses)
        """
        to_update.update(dict(
            deleted = True,
            last_fetch = datetime.utcnow(),
            score = 0,
        ))
        self.update(**to_update)
        self.remove_from_search_index()
        SortedSet(self.get_redis_key('last_fetched')).remove(self.id)
        SortedSet(self.get_redis_key('best_scored')).remove(self.id)

    def get_redis_key(self, key):
        """
        Return the specific redis key for the current model
        """
        return REDIS_KEYS[key][self.model_name]

    def get_content_template(self):
        """
        Return the name of the template used to display the object
        """
        return 'front/%s_content.html' % self.model_name

    def get_anonymous_template_content(self, context=None, regenerate=False, partial=True):
        """
        Return the anonymous content template for this object, updating it
        in cache if needed, with partial caching (parts for authenticated users
        are not cached)
        """
        if not context:
            context = Context(dict(
                STATIC_URL = settings.STATIC_URL,
            ))
        context.update({
            'obj': self,
            '__regenerate__': regenerate,
            '__partial__': partial,
        })

        return loader.get_template(self.get_content_template()).render(context)

    def update_cached_template(self, context=None):
        """
        Update the cached template
        """
        args = md5_constructor(urlquote(self.id))
        cache_key = 'template.cache.%s_content.%s' % (self.model_name, args.hexdigest())
        cache.delete(cache_key)
        self.get_anonymous_template_content(context, regenerate=True, partial=True)

    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        if not url_type.startswith(self.model_name):
            url_type = '%s_%s' % (self.model_name, url_type)
        params = copy(kwargs)
        if 'backend' not in params:
            params['backend'] = self.backend
        return (url_type, (), params)

    def get_absolute_url(self):
        """
        Home page url for this object
        """
        return self._get_url('home')

    def get_about_url(self):
        """
        About page url for this object
        """
        return self._get_url('about')

    def get_edit_tags_url(self):
        """
        Url to edit tags for this object
        """
        return self._get_url('edit_tags')

    def get_edit_note_url(self):
        """
        Url to edit the note for this object
        """
        return self._get_url('edit_note')

    def count_taggers(self):
        """
        Return the number of users with at least one tag on this object
        """
        # TODO : must be a better way (group by ?)
        return len(set(self.private_tags_class.objects.filter(content_object=self).values_list('owner', flat=True)))

    def count_tags(self, tags_type=None):
        """
        """
        queryset = self.private_tags
        if tags_type == 'places':
            queryset = queryset.filter(name__startswith='@')
        elif tags_type == 'projects':
            queryset = queryset.filter(name__startswith='#')
        elif tags_type == 'starred':
            queryset = queryset.filter(slug='starred')
        elif tags_type == 'check-later':
            queryset = queryset.filter(slug='check-later')
        elif tags_type == 'tags':
            queryset = queryset.exclude(name__startswith='#').exclude(name__startswith='@').exclude(slug='check-later').exclude(slug='starred')

        return queryset.count()


class Account(SyncableModel):
    """
    Represent an account from a backend
    How load an account, the good way :
        Account.objects.get_or_new(backend, slug)
    """
    model_name = 'account'
    model_name_plural = 'accounts'
    search_type = 'people'
    content_type = settings.CONTENT_TYPES['account']
    public_tags_class = PublicTaggedAccount
    private_tags_class = PrivateTaggedAccount

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'ACCOUNT_MIN_FETCH_DELTA', SyncableModel.MIN_FETCH_DELTA)
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'ACCOUNT_MIN_FETCH_RELATED_DELTA', SyncableModel.MIN_FETCH_RELATED_DELTA)
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'ACCOUNT_MIN_FETCH_DELTA_NEEDED', SyncableModel.MIN_FETCH_DELTA_NEEDED)
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'ACCOUNT_MIN_FETCH_RELATED_DELTA_NEEDED', SyncableModel.MIN_FETCH_RELATED_DELTA_NEEDED)
    # limit for auto fetch full
    MIN_FETCH_FULL_DELTA = getattr(settings, 'MIN_FETCH_FULL_DELTA', SyncableModel.MIN_FETCH_FULL_DELTA)

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
    for_list = OptimForListWithoutDeletedAccountManager()
    for_user_list = OptimForListAccountManager()

    # tags
    public_tags = TaggableManager(through=public_tags_class, related_name='public_on_accounts')
    private_tags = TaggableManager(through=private_tags_class, related_name='private_on_accounts')

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

    def fetch(self, token=None, log_stderr=False):
        """
        Fetch data from the provider
        """
        if not super(Account, self).fetch(token, log_stderr):
            return False

        try:
            self.get_backend().user_fetch(self, token=token)
        except BackendNotFoundError, e:
            if self.id:
                self.fake_delete()
            raise e
        else:
            self.deleted = False

        self.last_fetch = datetime.utcnow()

        if not self.official_following_count:
            self.following_modified = self.last_fetch
            self.following_count = 0
            if self.following_count:
                for following in self.following.all():
                    self.remove_following(following, False)

        if not self.official_followers_count:
            self.followers_modified = self.last_fetch
            self.followers_count = 0
            if self.followers_count:
                for follower in self.followers.all():
                    self.remove_follower(follower, False)

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

    def fetch_following(self, token=None):
        """
        Fetch the accounts followed by this account
        """
        return self.fetch_related_entries('user_following', 'following', 'following', 'slug', token=token)

    def add_following(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as followed by
        the current account.
        """
        return self.add_related_account_entry(account, 'following', 'followers', update_self_count)

    def remove_following(self, account, update_self_count=True):
        """
        Remove the given account from the ones followed by
        the current account
        """
        return self.remove_related_account_entry(account, 'following', 'followers', update_self_count)

    def fetch_followers(self, token=None):
        """
        Fetch the accounts following this account
        """
        return self.fetch_related_entries('user_followers', 'follower', 'followers', 'slug', token=token)

    def add_follower(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as follower of
        the current account.
        """
        return self.add_related_account_entry(account, 'followers', 'following', update_self_count)

    def remove_follower(self, account, update_self_count=True):
        """
        Remove the given account from the ones following
        the current account
        """
        return self.remove_related_account_entry(account, 'followers', 'following', update_self_count)

    def fetch_repositories(self, token=None):
        """
        Fetch the repositories owned/watched by this account
        """
        return self.fetch_related_entries('user_repositories', 'repository', 'repositories', 'project', token=token)

    def add_repository(self, repository, update_self_count=True):
        """
        Try to add the repository described by `repository` as one
        owner/watched by the current account.
        """
        return self.add_related_repository_entry(repository, 'repositories', 'followers', update_self_count)

    def remove_repository(self, repository, update_self_count):
        """
        Remove the given account from the ones the user own/watch
        """
        # mark the repository as deleted if it is removed from it's owner account
        if repository.owner_id and repository.owner_id == self.id:
            repository.fake_delete()

        return self.remove_related_repository_entry(repository, 'repositories', 'followers', update_self_count)

    @models.permalink
    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        (url_type, args, kwargs) = super(Account, self)._get_url(url_type, **kwargs)
        if 'slug' not in kwargs:
            kwargs['slug'] = self.slug
        return (url_type, args, kwargs)

    def get_followers_url(self):
        """
        Followers page url for this Account
        """
        return self._get_url('followers')

    def get_following_url(self):
        """
        Following page url for this Account
        """
        return self._get_url('following')

    def get_repositories_url(self):
        """
        Repositories page url for this Account
        """
        return self._get_url('repositories')

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

    def prepare_score(self):
        """
        Compute the current score for this account
        """
        parts, divider = super(Account, self).prepare_score()
        backend = self.get_backend()

        # boost if registered user
        if self.user_id:
            parts['user'] = 2

        if backend.supports('user_created_date'):
            now = datetime.utcnow()
            divider += 0.5
            if not self.official_created:
                parts['life_time'] = 0
            else:
                parts['life_time'] = self._compute_score_part((now - self.official_created).days / 90.0)

        if backend.supports('user_followers'):
            divider += 1
            parts['followers'] = self._compute_score_part(self.official_followers_count or 0)

        if backend.supports('repository_owner'):
            divider += 1
            repositories_score = []
            for repository in self.own_repositories.all():
                repo_parts, repo_divider = repository.prepare_main_score()
                repositories_score.append(self._compute_final_score(repo_parts, repo_divider))
            if repositories_score:
                min_score = sum(repositories_score) / float(len(repositories_score)) - 0.1
                repos = [score for score in repositories_score if score >= min_score]
                avg = sum(repos) / float(len(repos))
                parts['repositories'] = avg

        if backend.supports('repository_contributors'):
            divider += 1
            if self.contributing_count:
                parts['contributing'] = self._compute_score_part(self.contributing_count)


        #print parts
        return parts, divider

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
        # we use values for a big memory optimization on accounts with a lot of repositories
        rep_tagged_items = PublicTaggedRepository.objects.filter(content_object__followers=self).values('content_object__is_fork', 'content_object__owner__id', 'tag__slug', 'weight')
        for tagged_item in rep_tagged_items:
            divider = 1.0
            slug = tagged_item['tag__slug']
            if tagged_item['content_object__is_fork']:
                divider = 2
            if tagged_item['content_object__owner__id'] != self.id:
                divider = divider * 3
            if slug not in tags:
                tags[slug] = 0
            tags[slug] += (tagged_item['weight'] or 1) / divider

        tags = sorted(tags.iteritems(), key=lambda t: t[1], reverse=True)

        self.public_tags.set(tags[:5])

        # force cache update
        self.all_public_tags(force_cache=True)

    def all_public_tags(self, with_weight=False, force_cache=False):
        """
        Return all public tags for this account.
        Use this instead of self.public_tags.all() because
        we set the default order
        If `with_weight` is True, return the through model of the tagging
        system, with tags and weight.
        Else simply returns tags.
        in both cases, sort is by weight (desc) and slug (asc)
        """
        if not hasattr(self, '_all_public_tags'):
            self._all_user_tags = {}
        if with_weight not in self._all_user_tags:
            if with_weight:
                result = self.publictaggedaccount_set.select_related('tag').all()
            else:
                cache_key = self.get_redis_key('public_tags') % self.id
                tags = None
                if not force_cache:
                    tags = cache.get(cache_key)
                if tags is None:
                    tags = self.public_tags.order_by('-public_account_tags__weight', 'slug')
                    cache.set(cache_key, tags, 2678400)
                result = tags
            self._all_user_tags[with_weight] = result
        return self._all_user_tags[with_weight]

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

    def fetch_full_self_message(self):
        """
        Return the message part to display after a fetch of the object during a fetch_full
        """
        return 'fwr=%s, fwg=%s' % (self.official_followers_count, self.official_following_count)

    def fetch_full_related_message(self):
        """
        Return the message part to display after a fetch of the related during a fetch_full
        """
        return 'fwr=%s, fwg=%s, rep=%s' % (self.followers_count, self.following_count, self.repositories_count)

    def fetch_full_specific(self, depth=0, token=None, async=False):
        """
        After the full fetch of the account, try to make a full fetch of all
        related objects: repositories, followers, following
        """
        if depth > 0:
            depth -= 1

            # do fetch full for all repositories
            sys.stderr.write(" - full fetch of repositories (for %s)\n" % self)
            for repository in self.repositories.all():
                token, rep_fetch_error = repository.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

            # do fetch for all followers
            sys.stderr.write(" - full fetch of followers (for %s)\n" % self)
            for account in self.followers.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

            # do fetch for all following
            sys.stderr.write(" - full fetch of following (for %s)\n" % self)
            for account in self.following.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

    def get_search_index(self):
        """
        Return the search index for this model
        """
        return site.get_index(Account)

    def fake_delete(self):
        """
        Set the account as deleted and remove if from every automatic
        lists (not from ones created by users : tags, notes...)
        """
        to_update = {}
        now = datetime.utcnow()

        # manage following
        for account in self.following.all():
            account.update(
                followers_count = models.F('followers_count') - 1,
                raise_if_error = False
            )
        self.following.clear()
        to_update['following_count'] = 0
        to_update['following_modified'] = now

        # manage followers
        for account in self.followers.all():
            account.update(
                following_count = models.F('following_count') - 1,
                raise_if_error = False
            )
        self.followers.clear()
        to_update['followers_count'] = 0
        to_update['followers_modified'] = now

        # manage repositories
        for repository in self.repositories.all():
            if repository.owner_id == self.id:
                repository.fake_delete()
            else:
                repository.update(
                    followers_count = models.F('followers_count') - 1,
                raise_if_error = False
                )
        self.repositories.clear()
        to_update['repositories_count'] = 0
        to_update['repositories_modified'] = now

        # manage contributing
        for repository in self.contributing.all():
            repository.update(
                contributors_count = models.F('contributors_count') - 1,
                raise_if_error = False
            )
        self.contributing.clear()
        to_update['contributing_count'] = 0

        # final update
        to_update['user'] = None
        super(Account, self).fake_delete(to_update)

    def str_for_user(self, user):
        """
        Given a user, try to give a personified str for this account
        """
        user = offline_messages.get_user(user)
        default = super(Account, self).str_for_user(user)
        if not user or not self.user or self.user != user:
            return default
        return 'your account "%s"' % self


class Repository(SyncableModel):
    """
    Represent a repository from a backend
    How load a repository, the good way :
        Repository.objects.get_or_new(backend, project_name)
    """
    model_name = 'repository'
    model_name_plural = 'repositories'
    search_type = 'repositories'
    content_type = settings.CONTENT_TYPES['repository']
    public_tags_class = PublicTaggedRepository
    private_tags_class = PrivateTaggedRepository

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'REPOSITORY_MIN_FETCH_DELTA', SyncableModel.MIN_FETCH_DELTA)
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'REPOSITORY_MIN_FETCH_RELATED_DELTA', SyncableModel.MIN_FETCH_RELATED_DELTA)
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'REPOSITORY_MIN_FETCH_DELTA_NEEDED', SyncableModel.MIN_FETCH_DELTA_NEEDED)
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'REPOSITORY_MIN_FETCH_RELATED_DELTA_NEEDED', SyncableModel.MIN_FETCH_RELATED_DELTA_NEEDED)
    # limit for auto fetch full
    MIN_FETCH_FULL_DELTA = getattr(settings, 'MIN_FETCH_FULL_DELTA', SyncableModel.MIN_FETCH_FULL_DELTA)

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
    # Saved count
    forks_count = models.PositiveIntegerField(blank=True, null=True)

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
    for_list = OptimForListWithoutDeletedRepositoryManager()
    for_user_list = OptimForListRepositoryManager()

    # tags
    public_tags = TaggableManager(through=public_tags_class, related_name='public_on_repositories')
    private_tags = TaggableManager(through=private_tags_class, related_name='private_on_repositories')

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

    def fetch(self, token=None, log_stderr=False):
        """
        Fetch data from the provider
        """
        if not super(Repository, self).fetch(token, log_stderr):
            return False

        old_official_modified = self.official_modified

        try:
            self.get_backend().repository_fetch(self, token=token)
        except BackendNotFoundError, e:
            if self.id:
                self.fake_delete()
            raise e
        else:
            self.deleted = False

        self.last_fetch = datetime.utcnow()

        if not self.official_followers_count:
            self.followers_modified = self.last_fetch
            self.followers_count = 0
            if self.followers_count:
                for follower in self.followers.all():
                    self.remove_follower(follower, False)

        self.save()

        self._modified = old_official_modified < self.official_modified

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
            #owner.fetch(token=token)
            owner.fetch_full(token=token, async=True, async_priority=3, depth=0, allowed_interval=owner.MIN_FETCH_DELTA)
            fetched = True

        if save_needed:
            if not self.owner_id:
                self.owner = owner
            self.add_follower(owner, True)

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

        parent_is_new = False
        if not self.parent_fork_id:
            save_needed = True
            parent_fork = Repository.objects.get_or_new(self.backend,
                project=self.official_fork_of)
        else:
            parent_fork = self.parent_fork

        if parent_fork.fetch_needed():
            if parent_fork.is_new():
                parent_fork.forks_count = 1
            #parent_fork.fetch(token=token)
            parent_fork.fetch_full(token=token, async=True, async_priority=3, depth=0, allowed_interval=parent_fork.MIN_FETCH_DELTA)
            fetched = True

        if save_needed:
            if not self.parent_fork_id:
                self.parent_fork = parent_fork
            self.save()
            if not parent_is_new:
                self.parent_fork.update_count('forks', async=True)

        return fetched

    def fetch_followers(self, token=None):
        """
        Fetch the accounts following this repository
        """
        return self.fetch_related_entries('repository_followers', 'follower', 'followers', 'slug', token=token)

    def add_follower(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as follower of
        the current repository.
        """
        return self.add_related_account_entry(account, 'followers', 'repositories', update_self_count)

    def remove_follower(self, account, update_self_count=True):
        """
        Remove the given account from the ones following
        the Repository
        """
        return self.remove_related_account_entry(account, 'followers', 'repositories', update_self_count)

    def fetch_contributors(self, token=None):
        """
        Fetch the accounts following this repository
        """
        return self.fetch_related_entries('repository_contributors', 'contributor', 'contributors', 'slug', token=token)

    def add_contributor(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as contributor of
        the current repository.
        """
        return self.add_related_account_entry(account, 'contributors', 'contributing', update_self_count)

    def remove_contributor(self, account, update_self_count=True):
        """
        Remove the given account from the ones contributing to
        the Repository
        """
        return self.remove_related_account_entry(account, 'contributors', 'contributing', update_self_count)

    @models.permalink
    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        (url_type, args, kwargs) = super(Repository, self)._get_url(url_type, **kwargs)
        if 'project' not in kwargs:
            kwargs['project'] = self.project
        return (url_type, args, kwargs)

    def get_owner_url(self):
        """
        Url to the owner of this Repository
        """
        return self._get_url('owner')

    def get_followers_url(self):
        """
        Followers page url for this Repository
        """
        return self._get_url('followers')

    def get_contributors_url(self):
        """
        Contributors page url for this Repository
        """
        return self._get_url('contributors')

    def get_forks_url(self):
        """
        Forks page url for this Repository
        """
        return self._get_url('forks')

    def get_parent_fork_url(self):
        """
        Url to the parent fork of this Repository
        """
        return self._get_url('parent_fork')

    def get_readme_url(self):
        """
        Readme page url for this Repository
        """
        return self._get_url('readme')

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

        if not getattr(self, '_modified', True):
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

        self.readme_modified = datetime.utcnow()
        self.save()
        return True

    def prepare_main_score(self):
        """
        Compute the popularity of the repository, used to compute it's total
        score, and also to compute it's owner's score
        """
        backend = self.get_backend()

        divider = 0.0
        parts = dict(infos=0)

        # basic scores
        if self.name != self.slug:
            parts['infos'] += 0.3
        if self.description:
            parts['infos'] += 0.3
        if self.readme:
            parts['infos'] += 0.3

        if backend.supports('repository_created_date'):
            now = datetime.utcnow()
            divider += 0.5
            if not self.official_created:
                parts['life_time'] = 0
            else:
                parts['life_time'] = self._compute_score_part((now - self.official_created).days / 90.0)
                if backend.supports('repository_modified_date'):
                    if not self.official_modified or self.official_modified <= self.official_created:
                        # never updated, or updated before created ? seems to be a forked never touched
                        del parts['life_time']
                    else:
                        parts['zombie'] = - self._compute_score_part((now - self.official_modified).days / 90.0)
                else:
                    parts['life_time'] = parts['life_time'] / 2.0

        if backend.supports('repository_followers'):
            divider += 1
            parts['followers'] = self._compute_score_part(self.official_followers_count or 0)

        if backend.supports('repository_parent_fork'):
            divider += 1.0/3
            parts['forks'] = self._compute_score_part(self.official_forks_count or 0)

        if self.is_fork:
            divider = divider * 2

        return parts, divider

    def prepare_score(self):
        """
        Compute the current score for this repository
        """
        parts, divider = self.prepare_main_score()

        backend = self.get_backend()
        if backend.supports('repository_owner'):
            divider += 1
            if self.owner_id:
                owner_score = self.owner.score or self.owner.compute_score()
                parts['owner'] = self._compute_score_part(owner_score)

        #print parts
        return parts, divider

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
            known_tags = all_official_tags()
        rep_tags = get_tags_for_repository(self, known_tags)
        tags = sorted(rep_tags.iteritems(), key=lambda t: t[1], reverse=True)
        self.public_tags.set(tags[:5])

        # force cache update
        self.all_public_tags(force_cache=True)

    def all_public_tags(self, with_weight=False, force_cache=False):
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
            return self.publictaggedrepository_set.select_related('tag').all()
        else:
            cache_key = self.get_redis_key('public_tags') % self.id
            tags = None
            if not force_cache:
                tags = cache.get(cache_key)
            if tags is None:
                tags = self.public_tags.order_by('-public_repository_tags__weight', 'slug')
                cache.set(cache_key, tags, 2678400)
            return tags

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

    def fetch_full_self_message(self):
        """
        Return the message part to display after a fetch of the object during a fetch_full
        """
        return 'fwr=%s, frk=%s, is_frk=%s' % (self.official_followers_count, self.official_forks_count, self.is_fork)

    def fetch_full_related_message(self):
        """
        Return the message part to display after a fetch of the related during a fetch_full
        """
        return 'fwr=%s, ctb=%s' % (self.followers_count, self.contributors_count)

    def get_default_token(self):
        """
        Return the token object for this repository's owner
        """
        if self.owner_id:
            return self.get_backend().token_manager().get_for_account(self.owner)
        return None

    def fetch_full_specific(self, depth=0, token=None, async=False):
        """
        After the full fetch of the repository, try to make a full fetch of all
        related objects: owner, parent_fork, forks, contributors, followers
        """
        if depth > 0:
            depth -= 1

            # do fetch for all followers
            sys.stderr.write(" - full fetch of followers (for %s)\n" % self)
            for account in self.followers.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

            # do fetch for owner
            if self.owner_id:
                sys.stderr.write(" - full fetch of owner (for %s)\n" % self)
                token, rep_fetch_error = self.owner.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

            # do fetch for parent fork
            if self.is_fork and self.parent_fork_id:
                sys.stderr.write(" - full fetch of parent fork (for %s)\n" % self)
                token, rep_fetch_error = self.parent_fork.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

            # do fetch full for all forks
            sys.stderr.write(" - full fetch of forks (for %s)\n" % self)
            for repository in self.forks.all():
                token, rep_fetch_error = repository.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

            # do fetch for all contributors
            sys.stderr.write(" - full fetch of contributors (for %s)\n" % self)
            for account in self.contributors.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if self.should_stop_use_token(rep_fetch_error):
                    token = None

    def get_search_index(self):
        """
        Return the search index for this model
        """
        return site.get_index(Repository)

    def fake_delete(self):
        """
        Set the repository as deleted and remove if from every automatic
        lists (not from ones created by users : tags, notes...)
        """
        to_update = {}
        now = datetime.utcnow()

        # manage contributors
        for account in self.contributors.all():
            account.update(
                contributing_count = models.F('contributing_count') - 1,
                raise_if_error = False
            )
        self.contributors.clear()
        to_update['contributors_count'] = 0
        to_update['contributors_modified'] = now

        # manage child forks
        for fork in self.forks.all():
            fork.update(
                is_fork = False,
                official_fork_of = None,
            )
        self.forks.clear()
        to_update['forks_count'] = 0

        # manage parent fork
        if self.parent_fork_id:
            self.parent_fork.update(
                forks_count = models.F('forks_count') - 1,
                raise_if_error = False
            )
            to_update['parent_fork'] = None
            to_update['official_fork_of'] = None

        # manage followers
        for follower in self.followers.all():
            follower.update(
                repositories_count = models.F('repositories_count') - 1,
                raise_if_error = False
            )
        self.followers.clear()
        to_update['followers_count'] = 0
        to_update['followers_modified'] = now

        # final update
        to_update['owner'] = None
        super(Repository, self).fake_delete(to_update)


    def str_for_user(self, user):
        """
        Given a user, try to give a personified str for this repository
        """
        user = offline_messages.get_user(user)
        default = super(Repository, self).str_for_user(user)
        if not user or not self.owner.user or self.owner.user != user:
            return default
        return 'your repository "%s"' % self.slug


def get_object_from_str(object_str):
    """
    Try to get an object from its str representation, "core.account:123"
    (same represetation as returned by simple_str)
    """
    model_name, id = object_str.split(':')
    if '.' in model_name:
        model_name = model_name.split('.')[-1]

    if model_name == 'account':
        model = Account
    elif model_name == 'repository':
        model = Repository
    else:
        raise Exception('Invalid object')

    return model.objects.get(id=id)


from core.signals import *
