from django.shortcuts import render

from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    return render(request, 'core/repositories/home.html', dict(
        repository = repository,
    ))

@check_support('repository_followers')
@check_repository
def followers(request, backend, project, repository=None):
    """
    Page listing users following a repository
    """

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)
    if sort['key']:
        sorted_followers = repository.followers.order_by(sort['db_sort'])
    else:
        sorted_followers = repository.followers.all()

    return render(request, 'core/repositories/followers.html', dict(
        repository = repository,
        sorted_followers = sorted_followers,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))

@check_support('repository_contributors')
@check_repository
def contributors(request, backend, project, repository=None):
    """
    Page listing users contributing to a repository
    """

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)
    if sort['key']:
        sorted_contributors = repository.contributors.order_by(sort['db_sort'])
    else:
        sorted_contributors = repository.contributors.all()

    return render(request, 'core/repositories/contributors.html', dict(
        repository = repository,
        sorted_contributors = sorted_contributors,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))
