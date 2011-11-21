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
