from copy import copy

from django.db import models

from core.backends import get_backend
from core.exceptions import OriginalProviderLoginMissing

class AccountManager(models.Manager):
    """
    Manager for the Account model
    """

    def get_for_social_auth_user(self, social_auth_user):
        backend = social_auth_user.provider
        access_token = social_auth_user.extra_data.get('access_token', None)
        original_login = social_auth_user.extra_data.get('original_login', None)

        if not original_login:
            raise OriginalProviderLoginMissing(social_auth_user.user, backend)

        account = self.get_or_new(backend, original_login)
        account.access_token = access_token
        account.user = social_auth_user.user

        return account

    def get_or_new(self, backend, slug):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        """
        account = self.get_for_slug(backend, slug)
        if not account:
            account = self.model(backend=backend, slug=slug)
        return account

    def get_for_slug(self, backend, slug):
        """
        Try to return an existing account object for this backend/slug
        If not found, return None
        """
        try:
            return self.get(backend=backend, slug=slug)
        except:
            return None


class RepositoryManager(models.Manager):
    """
    Manager for the Repository model
    """

    def get_or_new(self, backend, project=None, **kwargs):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If the project is given, get params from it
        This way we can manage projects with user+slug or without user
        """
        backend = get_backend(backend)

        params = copy(kwargs)

        # get params from the project name
        if project:
            identifiers = backend.parse_project(project)
            for identifier in backend.needed_repository_identifiers:
                if identifiers.get(identifier, False):
                    params[identifier] = identifiers[identifier]

        # test that we have all needed params
        backend.assert_valid_repository_identifiers(**params)

        # remove empty params
        params = dict((key, value) for key, value in params.items()
            if key in backend.needed_repository_identifiers and value)
        params['backend'] = backend.name

        try:
            repository = self.get(**params)
        except self.model.DoesNotExist:
            repository = self.model(**params)

        return repository
