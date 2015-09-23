# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from os import walk
from os.path import basename

from django.conf import settings
from django.utils.importlib import import_module
from django.utils.functional import memoize

from core.exceptions import InvalidIdentifiersForProject, BackendError
from core.tokens import AccessTokenManager

#https://github.com/github/markup/
README_NAMES = ('README', 'readme',)
README_TYPES = (
    ('txt', ('', 'txt',)),
    ('rest', ('rst', 'rest',)),
    ('markdown', ('md', 'mkd', 'mkdn', 'mdown', 'markdown',)),
    ('textile', ('textile',)),
    ('rdoc', ('rdoc',)),
    ('org', ('org',)),
    ('mediawiki', ('mediawiki', 'wiki',)),
)

class BaseBackend(object):

    name = None
    auth_backend = None
    needed_repository_identifiers = ('slug',)
    support = dict(
        user_followers = False,
        user_following = False,
        user_repositories = False,
        user_created_date = False,
        repository_owner = False,
        repository_parent_fork = False,
        repository_followers = False,
        repository_contributors = False,
        repository_readme = False,
        repository_created_date = False,
        repository_modified_date = False,
    )

    def __init__(self, *args, **kwargs):
        """
        Add 2 supports values to fetch in one shot if the backends supports
        related for users or repositories
        """
        super(BaseBackend, self).__init__(*args, **kwargs)
        self._token_manager = None

        self.support['user_related'] = any([self.support.get('user_%s' % s, False)
            for s in ('followers', 'following', 'repositories')])
        self.support['repository_related'] = any([self.support.get('repository_%s' % s, False)
            for s in ('owner', 'fork', 'followers', 'contributors')])

    def token_manager(self):
        """
        Return the token manager for this backend
        """
        if not self._token_manager:
            self._token_manager = AccessTokenManager(self.name)
        return self._token_manager

    def supports(self, functionnality):
        """
        Return True if the functionnality is supported by the backend,
        regarding the `support` field. False by default
        """
        return self.support.get(functionnality, False)

    def get_exception(self, code, what, message=None):
        """
        Return an internal exception (BackendError)
        """
        return BackendError.make_for(self.name, code, what, message)

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

    def user_following(self, account, token=None):
        """
        Fetch the accounts followed by the given one
        """
        raise NotImplementedError('Implement in subclass')

    def user_followers(self, account, token=None):
        """
        Fetch the accounts following the given one
        """
        raise NotImplementedError('Implement in subclass')

    def user_repositories(self, account, token=None):
        """
        Fetch the repositories owned/watched by the given accont
        """
        raise NotImplementedError('Implement in subclass')

    def repository_project(self, repository, token=None):
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

    def repository_fetch(self, repository, token=None):
        """
        Fetch the repository from the provider and update the object
        """
        raise NotImplementedError('Implement in subclass')

    def repository_followers(self, repository, token=None):
        """
        Fetch the accounts following the given repository
        """
        raise NotImplementedError('Implement in subclass')

    def repository_contributors(self, repository, token=None):
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

    def repository_readme(self):
        """
        Try to get a readme in the repository
        """
        raise NotImplementedError('Implement in subclass')

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

def get_backend_from_auth(auth_backend_name):
    """
    Return a valid backend to use for a specified auth_backend, None in other case
    """
    backend_class = BACKENDS_BY_AUTH.get(auth_backend_name, None)
    if not backend_class:
        return None
    return get_backend(backend_class.name)
get_backend_from_auth.__cache = {}
get_backend = memoize(get_backend_from_auth, get_backend_from_auth.__cache, 1)

def get_backend(name):
    """
    Return a valid backend based on its name, None in other case
    """
    backend_class = BACKENDS_BY_AUTH.get(name, None)
    if not backend_class:
        return None
    return backend_class()
get_backend.__cache = {}
get_backend = memoize(get_backend, get_backend.__cache, 1)
