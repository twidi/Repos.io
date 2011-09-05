from django.shortcuts import render

from core.views.decorators import check_account

@check_account
def home(request, backend, slug, account=None):
    """
    Home page of an account
    """
    return render(request, 'core/accounts/home.html', dict(
        account = account,
    ))


@check_account
def followers(request, backend, slug, account=None):
    """
    Page listing accounts following an account
    """
    return render(request, 'core/accounts/followers.html', dict(
        account = account,
    ))

@check_account
def following(request, backend, slug, account=None):
    """
    Page listing accounts followed by an account
    """
    return render(request, 'core/accounts/following.html', dict(
        account = account,
    ))

@check_account
def repositories(request, backend, slug, account=None):
    """
    Page listing repositories owned/watched by an account
    """
    return render(request, 'core/accounts/repositories.html', dict(
        account = account,
    ))

