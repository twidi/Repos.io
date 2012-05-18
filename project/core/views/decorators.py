# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from functools import wraps

from django.http import Http404
from django.contrib import messages

from core.models import Account, Repository
from core.backends import get_backend


def check_account(function=None):
    """
    Check if an account identified by a backend and a slug exists
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, backend, slug, *args, **kwargs):
            try:
                account = Account.objects.get(backend=backend, slug=slug)
            except:
                raise Http404
            else:
                if account.deleted and view_func.__name__ != 'home':
                    messages.error(request, 'This page is useless since the account has been deleted')

                save_counts = set()
                if account.followers_count is None and account.get_backend().supports('user_followers'):
                    account.update_count('followers', save=False)
                    save_counts.add('followers')
                if account.following_count is None and account.get_backend().supports('user_following'):
                    account.update_count('following', save=False)
                    save_counts.add('following')
                if account.repositories_count is None and account.get_backend().supports('user_repositories'):
                    account.update_count('repositories', save=False)
                    save_counts.add('repositories')
                if account.contributing_count is None and account.get_backend().supports('user_repositories'):
                    account.update_count('contributing', save=False)
                    save_counts.add('contributing')
                if save_counts:
                    # update the object in DB, via an update, not a save
                    # if counts is "followers", add `followers_count=account.followers_count`
                    account.update(
                        **dict(('%s_count' % name, getattr(account, '%s_count' % name)) for name in save_counts)
                    )

                account.include_details = True
                kwargs['account'] = account
                return view_func(request, backend, slug, *args, **kwargs)

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)

def check_repository(function=None):
    """
    Check if a repository identified by a backend and a project exists
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, backend, project, *args, **kwargs):
            try:
                repository = Repository.objects.select_related('owner').select_related('owner', 'parent_fork', 'parent_fork_owner').get(backend=backend, project=project)
            except:
                raise Http404
            else:
                if repository.deleted and view_func.__name__ != 'home':
                    messages.error(request, 'This page is useless since the project has been deleted')

                save_counts = set()
                if repository.followers_count is None and repository.get_backend().supports('repository_followers'):
                    repository.update_count('followers', save=False)
                    save_counts.add('followers')
                if repository.contributors_count is None and repository.get_backend().supports('repository_contributors'):
                    repository.update_count('contributors', save=False)
                    save_counts.add('contributors')
                if repository.forks_count is None and repository.get_backend().supports('repository_parent_fork'):
                    repository.update_count('forks', save=False)
                    save_counts.add('forks')
                if save_counts:
                    # update the object in DB, via an update, not a save
                    # if counts is "followers", add `followers_count=repository.followers_count`
                    repository.update(
                        **dict(('%s_count' % name, getattr(repository, '%s_count' % name)) for name in save_counts)
                    )

                repository.include_details = True
                kwargs['repository'] = repository
                return view_func(request, backend, project, *args, **kwargs)

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)

def check_support(functionnality=None):
    """
    Check if the backend supports the given functionnality
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, backend, *args, **kwargs):
            try:
                if not get_backend(backend).supports(functionnality):
                    raise Http404
            except:
                raise Http404
            else:
                return view_func(request, backend, *args, **kwargs)

        return _view

    return _dec
