from django.shortcuts import render
from django.conf import settings

from utils.views import paginate
from core.models import Account
from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort
from tagging.flags import split_tags_and_flags

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    note = repository.get_user_note()
    private_tags = repository.get_user_tags()
    if private_tags:
        flags_and_tags = split_tags_and_flags(private_tags)
    else:
        flags_and_tags = None

    context = dict(
        note = note,
        repository = repository,
        flags_and_tags = flags_and_tags,
    )

    return render(request, 'core/repositories/home.html', context)

@check_support('repository_followers')
@check_repository
def followers(request, backend, project, repository=None):
    """
    Page listing users following a repository
    """

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    sorted_followers = Account.for_list.filter(repositories=repository)
    if sort['key']:
        sorted_followers = sorted_followers.order_by(sort['db_sort'])

    page = paginate(request, sorted_followers, settings.ACCOUNTS_PER_PAGE)

    return render(request, 'core/repositories/followers.html', dict(
        repository = repository,
        page = page,
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

    sorted_contributors = Account.for_list.filter(contributing=repository)
    if sort['key']:
        sorted_contributors = sorted_contributors.order_by(sort['db_sort'])

    page = paginate(request, sorted_contributors, settings.ACCOUNTS_PER_PAGE)

    return render(request, 'core/repositories/contributors.html', dict(
        repository = repository,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))
