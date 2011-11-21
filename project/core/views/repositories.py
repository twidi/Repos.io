# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render
from django.conf import settings

from utils.views import paginate
from core.models import Account, Repository
from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort, get_repository_sort

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    context = dict(repository = repository)
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

    context = dict(
        repository = repository,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )

    return render(request, 'core/repositories/followers.html', context)

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

    return render(request, 'core/repositories/contributors.html', context)

@check_support('repository_parent_fork')
@check_repository
def forks(request, backend, project, repository=None):
    """
    Page listing forks of a repository
    """

    mode = request.GET.get('mode')
    if mode not in ('real_forks', 'same_name',):
        mode = 'real_forks'

    sort = get_repository_sort(request.GET.get('sort_by', None), default='updated', default_reverse=True)

    if mode == 'real_forks':
        sorted_forks = Repository.for_list.filter(parent_fork=repository)
    else:
        sorted_forks = Repository.for_list.filter(name=repository.name).exclude(is_fork=True)

    if sort['key']:
        sorted_forks = sorted_forks.order_by(sort['db_sort'])

    page = paginate(request, sorted_forks, settings.REPOSITORIES_PER_PAGE)

    # check sub forks, one query / level
    if mode == 'real_forks':
        current_forks = page.object_list
        while True:
            by_id = dict((obj.id, obj) for obj in current_forks)
            current_forks = Repository.for_list.filter(parent_fork__in=by_id.keys()).order_by('-official_modified')
            if not current_forks:
                break
            for fork in current_forks:
                parent_fork = by_id[fork.parent_fork_id]
                if not hasattr(parent_fork, 'direct_forks'):
                    parent_fork.direct_forks = []
                parent_fork.direct_forks.append(fork)
        # make one list for each first level fork, to avoid recursion in templates
        all_forks = []
        def get_all_forks_for(fork, level):
            fork.fork_level = level
            all_subforks = [fork,]
            if hasattr(fork, 'direct_forks'):
                for subfork in fork.direct_forks:
                    all_subforks += get_all_forks_for(subfork, level+1)
                delattr(fork, 'direct_forks')
            return all_subforks
        for fork in page.object_list:
            all_forks += get_all_forks_for(fork, 0)
        page.object_list = all_forks

    context = dict(
        forks_mode = mode,
        repository = repository,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )

    return render(request, 'core/repositories/forks.html', context)


