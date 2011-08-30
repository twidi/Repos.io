from django.db import models

class AccountManager(models.Manager):
    """
    Manager for the Account model
    """

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

    def get_or_new(self, backend, slug, owner_name=None):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        """
        params = dict(backend=backend, slug=slug)
        if owner_name:
            params['officiel_owner'] = owner_name
        repository = self.get_for_owner_and_slug(**params)
        if not repository:
            repository = self.model(**params)
        return repository

    def get_for_owner_and_slug(self, backend, slug, owner_name=None):
        """
        Try to return an existing reopsitory object for this backend/slug.
        If the owner_name is given, use it.
        If not found, return None
        """
        params = dict(backend=backend, slug=slug)
        if owner_name:
            params['officiel_owner'] = owner_name
        try:
            return self.get(**params)
        except:
            return None
