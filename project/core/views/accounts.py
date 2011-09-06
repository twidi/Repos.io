from copy import copy

from django.shortcuts import render

from core.views.decorators import check_account

_sort_map = dict(
    # get_key = ('db_field', 'readable name'),
    name = ('slug_sort', 'project name'),
    owner = ('owner__slug_sort', 'owner'),
    updated = ('official_modified', 'update date'),
)

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

    # manage sort order

    sort_map = copy(_sort_map)

    repository_has_owner = account.get_backend().repository_has_owner
    if not repository_has_owner:
        del sort_map['owner']

    sort = request.GET.get('sort_by', 'name')
    if sort[0] == '-':
        sort = sort[1:]
        reverse = True
    else:
        reverse = False
    if sort not in sort_map:
        sort = 'name'
        reverse = False

    real_sort = sort_map[sort][0]
    if reverse:
        real_sort = '-' + real_sort

    sorted_repositories = account.repositories.order_by(real_sort).select_related('owner')

    return render(request, 'core/accounts/repositories.html', dict(
        account = account,
        sorted_repositories = sorted_repositories,
        sort = dict(
            key = sort,
            reverse = reverse,
            name = sort_map[sort][1],
            others = dict((key, value[1]) for key, value in sort_map.items() if key != sort),
        ),
        with_owners = repository_has_owner,
    ))

