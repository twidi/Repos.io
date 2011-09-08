from django.shortcuts import render

from core.views.decorators import check_account
from core.views.sort import get_repository_sort, get_account_sort

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

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)
    if sort['key']:
        sorted_followers = account.followers.order_by(sort['db_sort'])
    else:
        sorted_followers = account.followers.all()

    return render(request, 'core/accounts/followers.html', dict(
        account = account,
        sorted_followers = sorted_followers,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))

@check_account
def following(request, backend, slug, account=None):
    """
    Page listing accounts followed by an account
    """

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)
    if sort['key']:
        sorted_following = account.following.order_by(sort['db_sort'])
    else:
        sorted_following = account.following.all()

    return render(request, 'core/accounts/following.html', dict(
        account = account,
        sorted_following = sorted_following,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))

@check_account
def repositories(request, backend, slug, account=None):
    """
    Page listing repositories owned/watched by an account
    """

    sort_key = request.GET.get('sort_by', 'name')
    repository_has_owner = account.get_backend().supports('repository_owner')
    sort = get_repository_sort(sort_key, repository_has_owner)

    sorted_repositories = account.repositories.order_by(sort['db_sort']).select_related('owner')

    return render(request, 'core/accounts/repositories.html', dict(
        account = account,
        sorted_repositories = sorted_repositories,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        with_owners = repository_has_owner,
    ))

