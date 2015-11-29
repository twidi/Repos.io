# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from copy import copy
from datetime import datetime

from libgithub import ApiError, GitHub, JsonObject, RequestNotModified

from django.conf import settings

from core.backends import BaseBackend, NO_CACHE_HEADERS
from core.exceptions import SPECIFIC_ERROR_CODES


GITHUB_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class GithubBackend(BaseBackend):

    name = 'github'
    auth_backend = 'github'
    needed_repository_identifiers = ('slug', 'official_owner',)
    support = copy(BaseBackend.support)
    support.update(dict(
        user_followers = True,
        user_following = True,
        user_repositories = True,
        user_created_date = True,
        repository_owner = True,
        repository_parent_fork = True,
        repository_followers = True,
        repository_contributors = True,
        repository_readme = True,
        repository_created_date = True,
        repository_modified_date = True,
    ))

    def __init__(self, *args, **kwargs):
        """
        Create an empty dict to cache Github instances
        """
        super(GithubBackend, self).__init__(*args, **kwargs)
        self._github_instances = {}

    @classmethod
    def enabled(cls):
        """
        Return backend enabled status by checking basic settings
        """
        return all(hasattr(settings, name) for name in ('GITHUB_APP_ID', 'GITHUB_API_SECRET'))

    def _get_exception(self, exception, what):
        """
        Return an internal exception (BackendError)
        """
        code = None
        extra = {}
        if isinstance(exception, ApiError):
            code = exception.response.code
            try:
                headers = exception.response.headers
                if code == 403 and int(headers['x-ratelimit-remaining']) == 0:
                    code = SPECIFIC_ERROR_CODES ['SUSPENDED']
                    extra['suspended_until'] = headers.get('x-ratelimit-reset', 0)
            except Exception:
                code = exception.response.code
        try:
            message = exception.response.content
        except Exception:
            message = None
        return self.get_exception(code, what, message, extra)

    @classmethod
    def create_github_instance(cls, token, **default_headers):
        """
        Create a Github instance from the given parameters.
        """
        return GitHub(access_token=token, default_headers=default_headers)

    def github(self, token=None):
        """
        Return (and if not exists create and cache) a Github instance
        authenticated for the given token, or an anonymous one if
        there is no token
        """
        token = token or None
        str_token = str(token)
        if str_token not in self._github_instances:
            access_token = token.token if token else None
            self._github_instances[str_token] = self.create_github_instance(access_token)
        return self._github_instances[str_token]

    def user_fetch(self, account, token=None):
        """
        Fetch the account from the provider and update the object
        """
        # get/create the github instance
        github = self.github(token)

        # get user data fromgithub
        try:
            guser = github.users(account.slug).get()
        except Exception, e:
            raise self._get_exception(e, '%s' % account.slug)

        # associate github user and account
        rmap = self.user_map(guser)
        for key, value in rmap.items():
            setattr(account, key, value)

    def user_map(self, user):
        """
        Map the given user, which is an object (or dict)
        got from the backend, to a dict usable for creating/updating
        an Account core object
        # in this backend, we attend User objects only
        """
        simple_mapping = dict(
            slug = 'login',
            name = 'name',
            homepage = 'blog',
            avatar = 'avatar_url',
            official_created = 'created_at',
            official_followers_count = 'followers',
            official_following_count = 'following',
            url = 'html_url',
        )

        date_fields = ('official_created', )

        result = {}

        for internal_key, backend_key in simple_mapping.items():
            value = getattr(user, backend_key, None)
            if value is not None:
                if internal_key in date_fields:
                    value = datetime.strptime(value, GITHUB_DATE_FORMAT)
                result[internal_key] = value

        if 'avatar' not in result and getattr(user, 'gravatar_id', None):
                result['avatar'] = 'http://www.gravatar.com/avatar/%s' % user.gravatar_id

        if 'url' not in result:
            result['url'] = 'https://github.com/%s/' % user.login

        return result

    def iterate_pages(self, callable, start_page=1, per_page=100, request_headers=None, **kwargs):
        """"Iterate on each result for the githubpy callable, for each page

        Parameters
        ----------
        callable : libgithub._Callable
            The callable to execute for each page, for example ``github.users(slug).followers``
        start_page : int
            Default to 1, the number of page to start the page iteration
        per_page : int
            Default to 100 (the max), the number of results to ask Github for each page
        kwargs : dict
            Arguments to add on the query string for each page

        Returns
        -------
        generator
            A generator that will yield all entries from all pages, one by one

        Yields
        ------
        Account or Repository
            Depending on the caller, this generator will yield accounts or repositories

        """

        if not request_headers:
            request_headers = {}

        page = start_page
        while True:
            call_kwargs = {
                'page': page,
                'per_page': per_page,
            }
            call_kwargs.update(kwargs)

            if page > 1:
                request_headers.update(NO_CACHE_HEADERS)

            response_headers = {}
            try:
                for entry in callable.get(request_headers=request_headers,
                                          response_headers=response_headers, **call_kwargs):
                    yield entry
            except ApiError as e:
                # If the n page is a 404, we don't have this page, so we stop
                if page > 1 and e.code == 404:
                    break
                # Other exception, we raise it
                raise

            if 'link' not in response_headers:
                break

            links = self.parse_header_links(response_headers['link'])
            if 'next' not in links:
                break

            page += 1

    def user_following(self, account, token=None):
        """
        Fetch the accounts followed by the given one
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        result = []
        try:
            for guser in self.iterate_pages(github.users(account.slug).following):
                result.append(self.user_map(guser))
        except Exception, e:
            raise self._get_exception(e, '%s\'s following' % account.slug)

        return result

    def user_followers(self, account, token=None):
        """
        Fetch the accounts following the given one
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        result = []
        try:
            for guser in self.iterate_pages(github.users(account.slug).followers):
                result.append(self.user_map(guser))
        except Exception, e:
            raise self._get_exception(e, '%s\'s followers' % account.slug)

        return result

    def user_repositories(self, account, token=None):
        """
        Fetch the repositories owned/watched by the given accont
        """
        # get/create the github instance
        github = self.github(token)

        # get repositories data from github
        result = []
        found = {}

        request_headers = {}

        starred_modified = None
        owned_modified = None

        while True:

            # Starred repositories
            if not starred_modified:
                try:
                    for grepo in self.iterate_pages(github.users(account.slug).starred,
                                                    request_headers=request_headers):
                        repo = self.repository_map(grepo)
                        if repo['project'] not in found:
                            result.append(repo)
                            found[repo['project']] = True
                except RequestNotModified as e:
                    starred_modified = False
                except Exception as e:
                    raise self._get_exception(e, '%s\'s starred repositories' % account.slug)
                else:
                    starred_modified = True

            # Owned repositories
            if not owned_modified:
                try:
                    for grepo in self.iterate_pages(github.users(account.slug).repos,
                                                    request_headers=request_headers):
                        repo = self.repository_map(grepo)
                        if repo['project'] not in found:
                            result.append(repo)
                            found[repo['project']] = True
                except RequestNotModified as e:
                    owned_modified = False
                except Exception as e:
                    raise self._get_exception(e, '%s\'s owned repositories' % account.slug)
                else:
                    owned_modified = True

            # Both were modified, we can continue
            if starred_modified and owned_modified:
                return result

            # Both were not modified, we raise the BackendRequestNotModified exception
            if starred_modified is False and owned_modified is False:
                raise self._get_exception(e, '%s\'s owned repositories' % account.slug)

            # One was modified, but not the other: we restart without cache-control headers
            request_headers = NO_CACHE_HEADERS.copy()

    def repository_project(self, repository):
        """
        Return a project name the provider can use
        """
        if isinstance(repository, JsonObject):
            # a repository from githubpy
            owner = repository.owner.login
            slug = repository.name
        elif isinstance(repository, dict):
            # a mapped dict
            owner = repository['official_owner']
            slug = repository['slug']
        else:
            # a Repository object (from core.models)
            if repository.owner_id:
                owner = repository.owner.slug
            else:
                owner = repository.official_owner
            slug = repository.slug
        return '/'.join([owner, slug])

    def parse_project(self, project):
        """
        Try to get at least a slug, and if the backend can, a user
        by using the given project name
        """
        owner,  name = project.split('/')
        return dict(slug = name, official_owner = owner)

    def repository_fetch(self, repository, token=None):
        """
        Fetch the repository from the provider and update the object
        """
        # get/create the github instance
        github = self.github(token)

        # get repository data from github
        project = repository.get_project()
        project_parts = self.parse_project(project)
        try:
            grepo = github.repos(project_parts['official_owner'])(project_parts['slug']).get()
        except Exception, e:
            raise self._get_exception(e, '%s' % project)

        # associate github repo to core one
        rmap = self.repository_map(grepo)
        for key, value in rmap.items():
            setattr(repository, key, value)

    def repository_map(self, repository):
        """
        Map the given repository, which is an object (or dict)
        got from the backend, to a dict usable for creating/updating
        a Repository core object
        # in this backend, we attend Repository objects only
        """

        simple_mapping = dict(
            slug = 'name',
            name = 'name',
            url = 'html_url',
            description = 'description',
            homepage = 'homepage',
            official_owner = 'owner',  # WARNING : It's an object !
            official_forks_count = 'forks',
            official_fork_of = 'parent',  # WARNING : It's an object !
            official_followers_count = 'watchers',
            is_fork = 'fork',
            private = 'private',
            official_created = 'created_at',
            official_modified = 'pushed_at',
            default_branch = 'master_branch',
        )

        date_fields = ('official_created', 'official_modified', )

        result = {}

        for internal_key, backend_key in simple_mapping.items():
            value = getattr(repository, backend_key, None)
            if value is not None:
                if internal_key in date_fields:
                    value = datetime.strptime(value, GITHUB_DATE_FORMAT)
                result[internal_key] = value

        if 'official_owner' in result:
            result['official_owner'] = result['official_owner'].login
        if 'official_fork_of' in result:
            result['official_fork_of'] = self.repository_project(result['official_fork_of'])

        result['project'] = self.repository_project(result)

        return result

    def repository_followers(self, repository, token=None):
        """
        Fetch the accounts following the given repository
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        project = repository.get_project()
        project_parts = self.parse_project(project)
        result = []
        try:
            for guser in self.iterate_pages(
                github.repos(project_parts['official_owner'])(project_parts['slug']).stargazers
            ):
                result.append(self.user_map(guser))
        except Exception, e:
            raise self._get_exception(e, '%s\'s followers' % project)

        return result

    def repository_contributors(self, repository, token=None):
        """
        Fetch the accounts contributing the given repository
        For each account (dict) returned, the number of contributions is stored
        in ['__extra__']['contributions']
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        project = repository.get_project()
        project_parts = self.parse_project(project)
        result = []
        try:
            for guser in self.iterate_pages(
                github.repos(project_parts['official_owner'])(project_parts['slug']).contributors
            ):
                account_dict = self.user_map(guser)
                # TODO : nb of contributions not used yet but later...
                account_dict.setdefault('__extra__', {})['contributions'] = guser.contributions
                result.append(account_dict)
        except Exception, e:
            raise self._get_exception(e, '%s\'s contributors' % project)

        return result

    def repository_readme(self, repository, token=None):
        """
        Try to get a readme in the repository
        """
        # get/create the github instance
        github = self.github(token)

        project = repository.get_project()
        project_parts = self.parse_project(project)

        try:
            raw = github.repos(project_parts['official_owner'])(project_parts['slug']).readme.get(
                request_headers={'Accept': 'application/vnd.github.3.raw'}
            )
        except Exception, e:
            raise self._get_exception(e, '%s\'s readme file' % repository.project)

        try:
            # no cache control here. If the raw was updated, we force the retrieval of the html
            html = github.repos(project_parts['official_owner'])(project_parts['slug']).readme.get(
                request_headers=dict(NO_CACHE_HEADERS, Accept='application/vnd.github.3.html')
            )
        except Exception, e:
            raise self._get_exception(e, '%s\'s readme file' % repository.project)

        return raw, html


BACKENDS = {'github': GithubBackend, }
