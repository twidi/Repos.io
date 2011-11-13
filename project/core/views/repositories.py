from django.shortcuts import render
from django.conf import settings

from utils.views import paginate
from core.models import Account, Repository
from core.views import context_private_part
from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort, get_repository_sort

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

@check_support('repository_parent_fork')
@check_repository
def forks(request, backend, project, repository=None):
    """
    Page listing forks of a repository
    """

    sort = get_repository_sort(request.GET.get('sort_by', None), default='updated', default_reverse=True)

    sorted_forks = Repository.for_list.filter(parent_fork=repository)
    if sort['key']:
        sorted_forks = sorted_forks.order_by(sort['db_sort'])

    page = paginate(request, sorted_forks, settings.REPOSITORIES_PER_PAGE)

    all_displayed_repositories = list(page.object_list)

    # check sub forks, one query / level
    current_forks = page.object_list
    while True:
        by_id = dict((obj.id, obj) for obj in current_forks)
        current_forks = Repository.for_list.filter(parent_fork__in=by_id.keys()).order_by('-official_modified')
        if not current_forks:
            break
        all_displayed_repositories += list(current_forks)
        for fork in current_forks:
            parent_fork = by_id[fork.parent_fork_id]
            if not hasattr(parent_fork, 'direct_forks'):
                parent_fork.direct_forks = []
            parent_fork.direct_forks.append(fork)

    context = dict(
        repository = repository,
        page = page,
        all_displayed = all_displayed_repositories,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )

    return _render_with_private(request, 'core/repositories/forks.html', context)


