from django.shortcuts import render
from django.conf import settings

from utils.views import paginate
from core.models import Account
from core.views import context_private_part
from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort

def _render_with_private(request, template, context):
    context.update(context_private_part(context['repository']))
    return render(request, template, context)

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    context = dict(repository = repository)
    return _render_with_private(request, 'core/repositories/home.html', context)

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

    context = dict(
        repository = repository,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )

    return _render_with_private(request, 'core/repositories/followers.html', context)

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

    context = dict(
        repository = repository,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )

    return _render_with_private(request, 'core/repositories/contributors.html', context)
