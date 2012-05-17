# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from copy import copy
import base64

from pygithub3 import Github
from pygithub3.services.repos import Repo
from pygithub3.exceptions import NotFound
from requests.exceptions import HTTPError

from django.conf import settings

from core.backends import BaseBackend, README_NAMES, README_TYPES


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

    def _get_exception(self, exception, what, token=None):
        """
        Return an internal exception (BackendError)
        """
        code = None
        if isinstance(exception, HTTPError):
            code = exception.response.status_code
        elif isinstance(exception, NotFound):
            code = 404
        return self.get_exception(code, what)

    def create_github_instance(self, *args, **kwargs):
        """
        Create a Github instance from the given parameters.
        Add, if not provided, the `requests_per_second` and `cache` ones.
        """
        if 'per_page' not in kwargs:
            kwargs['per_page'] = 100
        return Github(*args, **kwargs)

    def github(self, token=None):
        """
        Return (and if not exists create and cache) a Github instance
        authenticated for the given token, or an anonymous one if
        there is no token
        """
        token = token or None
        str_token = str(token)
        if str_token not in self._github_instances:
            params = {}
            if token:
                params['token'] = token.token
            self._github_instances[str_token] = self.create_github_instance(**params)
        return self._github_instances[str_token]

    def user_fetch(self, account, token=None):
        """
        Fetch the account from the provider and update the object
        """
        # get/create the github instance
        github = self.github(token)

        # get user data fromgithub
        try:
            guser = github.users.get(account.slug)
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

        result = {}

        for internal_key, backend_key in simple_mapping.items():
            value = getattr(user, backend_key, None)
            if value is not None:
                result[internal_key] = value

        if 'avatar' not in result and getattr(user, 'gravatar_id', None):
                result['avatar'] = 'http://www.gravatar.com/avatar/%s' % user.gravatar_id

        if 'url' not in result:
            result['url'] = 'https://github.com/%s/' % user.login

        return result

    def user_following(self, account, token=None):
        """
        Fetch the accounts followed by the given one
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        result = []
        try:
            for guser in github.users.followers.list_following(account.slug).iterator():
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
            for guser in github.users.followers.list(account.slug).iterator():
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
        try:
            for grepo in github.repos.watchers.list_repos(account.slug).iterator():
                result.append(self.repository_map(grepo))
        except Exception, e:
            raise self._get_exception(e, '%s\'s repositories' % account.slug)

        return result

    def repository_project(self, repository):
        """
        Return a project name the provider can use
        """
        if isinstance(repository, dict):
            if 'official_owner' in repository:
                # a mapped dict
                owner = repository['official_owner']
                slug = repository['slug']
        elif isinstance(repository, Repo):
            # a repository from pygithub3
            owner = repository.owner.login
            slug = repository.name
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

        # get repository data fromgithub
        project = repository.get_project()
        project_parts = self.parse_project(project)
        try:
            grepo = github.repos.get(project_parts['official_owner'], project_parts['slug'])
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

        result = {}

        for internal_key, backend_key in simple_mapping.items():
            value = getattr(repository, backend_key, None)
            if value is not None:
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
            for guser in github.repos.watchers.list(project_parts['official_owner'], project_parts['slug']).iterator():
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
            for guser in github.repos.list_contributors(project_parts['official_owner'], project_parts['slug']).iterator():
                account_dict = self.user_map(guser)
                # TODO : nb of contributions not used yet but later...
                account_dict.setdefault('__extra__', {})['contributions'] = guser.contributions
                result.append(account_dict)
        except Exception, e:
            raise self._get_exception(e, '%s\'s followers' % project)

        return result

    def repository_readme(self, repository, token=None):
        """
        Try to get a readme in the repository
        """
        # get/create the github instance
        github = self.github(token)

        project = repository.get_project()
        project_parts = self.parse_project(project)

        empty_readme = ('', None)

        # get all files at the root of the project
        try:
            tree = github.git_data.trees.get(
                sha = repository.default_branch or 'master',
                recursive = None,
                user = project_parts['official_owner'],
                repo = project_parts['slug'],
            )
        except NotFound:
            return empty_readme
        except Exception, e:
            raise self._get_exception(e, '%s\'s readme' % project)

        # filter readme files
        files = [f for f in tree.tree if f.get('type', None) == 'blob'
            and 'path' in f and any(f['path'].startswith(n) for n in README_NAMES)]

        # not readme file found, exit
        if not files:
            return empty_readme

        # get contents for all these files
        contents = []
        for fil in files:
            filename = fil['path']
            try:
                blob = github.git_data.blobs.get(
                    sha = fil['sha'],
                    user = project_parts['official_owner'],
                    repo = project_parts['slug'],
                )
            except NotFound:
                continue
            except Exception, e:
                raise self._get_exception(e, '%s\'s readme file' % repository.project)
            else:
                try:
                    content = blob.content
                    if blob.encoding == 'base64':
                        content = base64.decodestring(content)
                    contents.append((filename, content))
                except:
                    return empty_readme

        if not contents:
            return empty_readme

        # keep the biggest
        filename, content = sorted(contents, key=len)[-1]

        # find the type
        filetype = 'txt'
        try:
            extension = filename.split('.')[-1]
            for ftype, extensions in README_TYPES:
                if extension in extensions:
                    filetype = ftype
                    break
        except:
            pass

        return content, filetype


BACKENDS = {'github': GithubBackend, }
