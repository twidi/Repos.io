from os import walk
from os.path import basename

from django.conf import settings
from django.utils.importlib import import_module

from core.exceptions import InvalidIdentifiersForProject

class BaseBackend(object):

    name = None
    needed_repository_identifiers = ('slug',)

    def user_fetch(self, account):
        """
        Fetch the account from the provider and update the account
        """
        raise NotImplementedError('Implement in subclass')

    def repository_project(self, repository):
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

    def repository_fetch(self, repository, access_token=None):
        """
        Fetch the repository from the provider and update the object
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
    enabled_backends = getattr(settings, 'CORE_ENABLED_BACKENDS', ('github',))

    mod_name = 'core.backends'
    mod = import_module('core.backends')

    for directory, subdir, files in walk(mod.__path__[0]):
        for name in filter(lambda name: name.endswith('.py') and not name.startswith('_'), files):
            try:
                name = basename(name).replace('.py', '')
                sub = import_module(mod_name + '.' + name)
                # register only enabled backends
                backends.update(((key, val)
                                    for key, val in sub.BACKENDS.items()
                                        if val.enabled() and
                                           (not enabled_backends or
                                            key in enabled_backends)))
            except (ImportError, AttributeError):
                pass
    return backends

# load backends from defined modules
BACKENDS = get_backends()

def get_backend(name, *args, **kwargs):
    """Return auth backend instance *if* it's registered, None in other case"""
    return BACKENDS.get(name, lambda *args, **kwargs: None)(*args, **kwargs)
