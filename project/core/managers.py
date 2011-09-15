from copy import copy

from django.db import models

from core.backends import get_backend, get_backend_from_auth
from core.exceptions import OriginalProviderLoginMissing
from core.utils import slugify

class SyncableModelManager(models.Manager):
    """
    Base manager for all syncable models
    """

    def get_last_fetched(self, length=20):
        """
        Return the last fetch objects
        """
        result = self.filter(last_fetch__isnull=False).order_by('-last_fetch')
        if length:
            result = result[:length]
        return result


class AccountManager(SyncableModelManager):
    """
    Manager for the Account model
    """

    def get_for_social_auth_user(self, social_auth_user):
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


class RepositoryManager(SyncableModelManager):
    """
    Manager for the Repository model
    """

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
            repository = self.get(backend=backend, **identifiers)
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

    def get_last_fetched(self, length=20):
        """
        Return the last fetch repositories, with owners
        """
        result = super(RepositoryManager, self).get_last_fetched(length=None).select_related('owner')
        if length:
            result = result[:length]
        return result
