from os import walk
from os.path import basename

from django.conf import settings
from django.utils.importlib import import_module

from core.exceptions import InvalidIdentifiersForProject, BackendError

class BaseBackend(object):

    name = None
    auth_backend = None
    needed_repository_identifiers = ('slug',)
    repository_has_owner = False

    def get_exception(self, code, object_type, object_name):
        """
        Return an internal exception (BackendError)
        """
        return BackendError.make_for(self.name, code, object_type, object_name)

    def user_map(self, user):
        """
        Map the given user, which is an object (or dict, or...)
        got from the backend, to a dict usable for creating/updating
        an Account core object
        """
        raise NotImplementedError('Implement in subclass')

    def user_fetch(self, account):
        """
        Fetch the account from the provider and update the account
        """
        raise NotImplementedError('Implement in subclass')

    def user_following(self, account, access_token=None):
        """
        Fetch the accounts followed by the given one
        """
        raise NotImplementedError('Implement in subclass')

    def user_followers(self, account, access_token=None):
        """
        Fetch the accounts following the given one
        """
        raise NotImplementedError('Implement in subclass')

    def user_repositories(self, account, access_token=None):
        """
        Fetch the repositories owned/watched by the given accont
        """
        raise NotImplementedError('Implement in subclass')

    def repository_project(self, repository, access_token=None):
        """
        Return a project name the provider can use
        """
        raise NotImplementedError('Implement in subclass')

    def parse_project(self, project):
        """
        Try to get at least a slug, and if the backend can, a user
        by using the given project name
        """
        raise NotImplementedError('Implement in subclass')

    def repository_map(self, repository):
        """
        Map the given repository, which is an object (or dict, or...)
        got from the backend, to a dict usable for creating/updating
        a Repository core object
        """
        raise NotImplementedError('Implement in subclass')

    def repository_fetch(self, repository, access_token=None):
        """
        Fetch the repository from the provider and update the object
        """
        raise NotImplementedError('Implement in subclass')

    def repository_followers(self, repository, access_token=None):
        """
        Fetch the accounts following the given repository
        """
        raise NotImplementedError('Implement in subclass')

    def repository_contributors(self, repository, access_token=None):
        """
        Fetch the accounts contributing the given repository
        For each account (dict) returned, the number of contributions is stored
        in ['__extra__']['contributions']
        """
        raise NotImplementedError('Implement in subclass')

    def assert_valid_repository_identifiers(self, **kwargs):
        """
        Test kwargs to check if we have all needed parameters to identify a project
        """
        for identifier in self.needed_repository_identifiers:
            if not kwargs.get(identifier, False):
                raise InvalidIdentifiersForProject(self)

    @classmethod
    def enabled(cls):
        """
        By default backends are not enabled
        """
        return False


def get_backends():
    """
    Get all wanted available backends (inspired by django-social-auth)
    """
    backends = {}
    backends_by_auth = {}
    enabled_backends = getattr(settings, 'CORE_ENABLED_BACKENDS', ('github',))

    mod_name = 'core.backends'
    mod = import_module('core.backends')

    for directory, subdir, files in walk(mod.__path__[0]):
        for name in filter(lambda name: name.endswith('.py') and not name.startswith('_'), files):
            try:
                name = basename(name).replace('.py', '')
                sub = import_module(mod_name + '.' + name)
                # register only enabled backends
                new_backends = dict((key, val)
                                    for key, val in sub.BACKENDS.items()
                                        if val.name and val.enabled() and
                                           (not enabled_backends or
                                            key in enabled_backends))

                backends.update(new_backends)

                backends_by_auth.update((backend.auth_backend, backend)
                        for backend in new_backends.values()
                            if backend.auth_backend)

            except (ImportError, AttributeError):
                pass

    return backends, backends_by_auth

# load backends from defined modules
BACKENDS, BACKENDS_BY_AUTH = get_backends()

def get_backend_from_auth(auth_backend):
    """
    Return the backend to use for a specified auth backend
    """
    return BACKENDS_BY_AUTH.get(auth_backend, None)

def get_backend(name, *args, **kwargs):
    """Return auth backend instance *if* it's registered, None in other case"""
    return BACKENDS.get(name, lambda *args, **kwargs: None)(*args, **kwargs)
