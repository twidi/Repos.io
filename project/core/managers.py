from copy import copy

from django.db import models
from django.conf import settings

from redisco import connection

from core import REDIS_KEYS
from core.backends import get_backend, get_backend_from_auth
from core.exceptions import OriginalProviderLoginMissing
from core.core_utils import slugify
from core.tokens import AccessToken

class SyncableModelManager(models.Manager):
    """
    Base manager for all syncable models
    """

    def get_redis_key(self, key):
        """
        Return the specific redis key for the current model
        """
        return REDIS_KEYS[key][self.model_name]

    def get_best_in_zset(self, key, size):
        """
        Return the `size` items with the best score in the given zset
        """
        ids = map(int, connection.zrevrange(self.get_redis_key(key), 0, size-1))
        objects = self.in_bulk(ids)
        return [objects[id] for id in ids if id in objects]

    def get_last_fetched(self, size=20):
        """
        Return the last `size` fetched objects
        """
        return self.get_best_in_zset('last_fetched', size)

    def get_best(self, size=20):
        """
        Return the `size` objects with the better score
        """
        return self.get_best_in_zset('best_scored', size)


class AccountManager(SyncableModelManager):
    """
    Manager for the Account model
    """
    model_name = 'account'

    def associate_to_social_auth_user(self, social_auth_user, is_new):
        auth_backend = social_auth_user.provider
        backend = get_backend_from_auth(auth_backend)

        access_token = social_auth_user.extra_data.get('access_token', None)
        original_login = social_auth_user.extra_data.get('original_login', None)

        if not original_login:
            raise OriginalProviderLoginMissing(social_auth_user.user, backend.name)

        account = self.get_or_new(backend.name, original_login)
        account.access_token = access_token
        account.user = social_auth_user.user

        if account.fetch_needed():
            account.fetch()
        else:
            account.save()

        token = None
        if access_token:
            token = account.get_default_token()
            if not token:
                token = AccessToken.objects.create(
                    backend = account.backend,
                    login = account.slug,
                    token = access_token
                )

        account.fetch_full(
            token = token,
            depth = 2 if is_new else 1,
            async = True,
            async_priority = 3 if is_new else 2,
        )

        return account

    def get_or_new(self, backend, slug, **defaults):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If defaults is given, it's content will be used to create the new Account
        """
        account = self.get_for_slug(backend, slug)
        if account:
            if defaults:
                account.update_many_fields(**defaults)
        else:
            defaults = copy(defaults)
            allowed_fields = self.model._meta.get_all_field_names()
            defaults = dict((key, value) for key, value in defaults.items()
                if key in allowed_fields)
            defaults['backend'] = backend
            defaults['slug'] = slug
            account = self.model(**defaults)
        return account

    def get_for_slug(self, backend, slug):
        """
        Try to return an existing account object for this backend/slug
        If not found, return None
        """
        try:
            return self.get(backend=backend, slug_lower=slug.lower())
        except:
            return None


class OptimForListAccountManager(AccountManager):
    """
    Default `only` (fetch only some fields) and `select_related`
    """

    list_needed_fields = ('backend', 'status', 'slug', 'name', 'last_fetch', 'avatar', 'score', 'url', 'homepage', 'modified')
    list_select_related = ()

    def get_query_set(self):
        return super(OptimForListAccountManager, self).get_query_set().only(*self.list_needed_fields).select_related(*self.list_select_related)


class RepositoryManager(SyncableModelManager):
    """
    Manager for the Repository model
    """
    model_name = 'repository'

    def get_or_new(self, backend, project=None, **defaults):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If the project is given, get params from it
        This way we can manage projects with user+slug or without user
        """
        backend = get_backend(backend)

        defaults = copy(defaults)

        # get params from the project name
        if project:
            identifiers = backend.parse_project(project)
            for identifier in backend.needed_repository_identifiers:
                if identifiers.get(identifier, False):
                    defaults[identifier] = identifiers[identifier]

        # test that we have all needed defaults
        backend.assert_valid_repository_identifiers(**defaults)

        try:
            identifiers = dict((key, defaults[key].lower())
                for key in backend.needed_repository_identifiers)
            if 'slug' in identifiers and 'slug_lower' not in identifiers:
                identifiers['slug_lower'] = identifiers['slug']
                del identifiers['slug']
            if 'official_owner' in identifiers and 'official_owner_lower' not in identifiers:
                identifiers['official_owner_lower'] = identifiers['official_owner']
                del identifiers['official_owner']
            repository = self.get(backend=backend.name, **identifiers)
        except self.model.DoesNotExist:
            # remove empty defaults
            allowed_fields = self.model._meta.get_all_field_names()
            defaults = dict((key, value) for key, value in defaults.items()
                if key in allowed_fields)
            defaults['backend'] = backend.name

            repository = self.model(**defaults)
        else:
            if defaults:
                repository.update_many_fields(**defaults)

        return repository

    def slugify_project(self, project):
        """
        Slugify each part of a project, but keep the slashes
        """
        return '/'.join([slugify(part) for part in project.split('/')])


class OptimForListRepositoryManager(RepositoryManager):
    """
    Default `only` (fetch only some fields) and `select_related`
    """

    # default fields for wanted repositories
    list_needed_fields = ['backend', 'status', 'project', 'slug', 'name', 'last_fetch', 'logo', 'score', 'is_fork', 'description', 'official_modified', 'owner', 'parent_fork', 'official_created', 'modified']
    # same for the parent fork
    list_needed_fields += ['parent_fork__%s' % field for field in list_needed_fields if field not in ('is_fork', 'parent_fork', 'description', 'official_created')]
    # and needed ones for owners
    list_needed_fields += ['owner__%s' % field for field in OptimForListAccountManager.list_needed_fields]
    list_needed_fields += ['parent_fork__owner__%s' % field for field in ('name', 'slug', 'status', 'backend', 'last_fetch')]

    list_select_related = ('owner', 'parent_fork', 'parent_fork__owner',)

    def get_query_set(self):
        return super(OptimForListRepositoryManager, self).get_query_set().only(*self.list_needed_fields).select_related(*self.list_select_related)
