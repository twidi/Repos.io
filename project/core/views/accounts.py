from django.shortcuts import render

from core.views.decorators import check_account

@check_account
def home(request, backend, slug, account=None):
    """
    Home page of a user
    """
    return render(request, 'core/users/home.html', dict(
        account = account,
    ))


@check_account
def followers(request, backend, slug, account=None):
    """
    Page listing users following a user
    """
    return render(request, 'core/users/followers.html', dict(
        account = account,
    ))

@check_account
def following(request, backend, slug, account=None):
    """
    Page listing users followed by a user
    """
    return render(request, 'core/users/following.html', dict(
        account = account,
    ))

@check_account
def repositories(request, backend, slug, account=None):
    """
    Page listing repositories owned/watched by a user
    """
    return render(request, 'core/users/repositories.html', dict(
        account = account,
    ))

