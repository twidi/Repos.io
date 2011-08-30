from github2.client import Github

from django.conf import settings

from core.backends import BaseBackend

class GithubBackend(BaseBackend):

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

    def create_github_instance(self, *args, **kwargs):
        """
        Create a Github instance from the given parameters.
        Add, if not provided, the `requests_per_second` and `cache` ones.
        """
        kwargs.setdefault('requests_per_second', 1)
        # for debugging, only if set
        if getattr(settings, 'GITHUB_CACHE_DIR', None):
            kwargs.setdefault('cache', settings.GITHUB_CACHE_DIR)
        return Github(*args, **kwargs)

    def github(self, access_token=None):
        """
        Return (and if not exists create and cache) a Github instance
        authenticated for the given access_token, or an anonymous one if
        there is no access_token
        """
        access_token = access_token or None
        if access_token not in self._github_instances:
            self._github_instances[access_token] = self.create_github_instance(access_token=access_token)
        return self._github_instances[access_token]

    def user_fetch(self, account, access_token=None):
        """
        Fetch the account from the provider and update the object
        """
        # get/create the github instance
        github = self.github(access_token)

        # get user data fromgithub
        guser = github.users.show(account.slug)

        # associate github user and account

        account.name = guser.name

        if getattr(guser, 'avatar_url', None):
            account.avatar = guser.avatar_url
        elif getattr(guser, 'gravatar_id', None):
            account.avatar = 'http://www.gravatar.com/avatar/%s' % guser.gravatar_id

        account.since = guser.created_at
        account.homepage = guser.blog

        account.official_followers_count = guser.followers_count
        account.official_following_count = guser.following_count

    def repository_project(self, repository):
        """
        Return a project name the provider can user
        """
        if repository.owner_id:
            owner = repository.owner.slug
        else:
            owner = repository.official_owner
        return self.github().project_for_user_repo(owner, repository.slug)


    def repository_fetch(self, repository, access_token=None):
        """
        Fetch the repository from the provider and update the object
        """
        # get/create the github instance
        github = self.github(access_token)

        # get repository data fromgithub
        project = repository.get_project()
        grepo = github.repos.info(project)

        # associate github user and account
        repository.name = grepo.name
        repository.url = grepo.url
        repository.description = grepo.description
        repository.homepage = grepo.homepage
        repository.project = project
        repository.official_owner = grepo.owner
        repository.official_forks_count = grepo.forks
        repository.official_fork_of = grepo.parent
        repository.official_followers_count = grepo.watchers
        repository.is_fork = grepo.fork

BACKENDS = { 'github': GithubBackend, }
