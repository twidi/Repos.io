from django.http import Http404

from core.models import Account, Repository

def check_account(function=None):
    """
    Check if an account identified by a backend and a slug exists
    """
    def _dec(view_func):
        def _view(request, backend, slug, *args, **kwargs):
            try:
                account = Account.objects.get(backend=backend, slug=slug)
            except:
                raise Http404
            else:
                kwargs['account'] = account
                return view_func(request, backend, slug, *args, **kwargs)

        _view.__name__ = view_func.__name__
        _view.__dict__ = view_func.__dict__
        _view.__doc__ = view_func.__doc__

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
        def _view(request, backend, project, *args, **kwargs):
            try:
                repository = Repository.objects.select_related('owner').get(backend=backend, project=project)
            except:
                raise Http404
            else:
                kwargs['repository'] = repository
                return view_func(request, backend, project, *args, **kwargs)

        _view.__name__ = view_func.__name__
        _view.__dict__ = view_func.__dict__
        _view.__doc__ = view_func.__doc__

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)
