from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings

def check_account(function=None):
    """
    Check if a given login/provider is linked to the current user
    """
    def _dec(view_func):
        def _view(request, login, provider, *args, **kwargs):
            user = request.user
            if not user.is_authenticated():
                return HttpResponseRedirect(settings.LOGIN_URL)
            if login and provider:
                associated = user.social_auth.all()
                for social_user in associated:
                    if social_user.provider == provider and social_user.extra_data.get('original_login', None) == login:
                        kwargs['social_user'] = social_user
                        return view_func(request, login, provider, *args, **kwargs)

            return HttpResponseForbidden("This account is not associated with your account")

        _view.__name__ = view_func.__name__
        _view.__dict__ = view_func.__dict__
        _view.__doc__ = view_func.__doc__

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)
