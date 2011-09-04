from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings

def check_account(function=None):
    """
    Check if a given slug/backend is linked to the current user
    """
    def _dec(view_func):
        def _view(request, slug, backend, *args, **kwargs):
            user = request.user
            if not user.is_authenticated():
                return HttpResponseRedirect(settings.LOGIN_URL)
            try:
                account = request.user.accounts.get(backend=backend, slug=slug)
            except:
                return HttpResponseForbidden("This account is not associated with your account")
            else:
                kwargs['account'] = account
                return view_func(request, slug, backend, *args, **kwargs)

        _view.__name__ = view_func.__name__
        _view.__dict__ = view_func.__dict__
        _view.__doc__ = view_func.__doc__

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)
