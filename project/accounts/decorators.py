# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from functools import wraps

from django.conf import settings
from django.http import HttpResponseRedirect

def anonymous_required(function=None):
    """
    Check if the user is anonymous, else redirect it
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, *args, **kwargs):
            if request.user is not None and request.user.is_authenticated():
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            return view_func( request, *args, **kwargs )

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)
