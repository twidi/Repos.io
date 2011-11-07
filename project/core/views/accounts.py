from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings

from utils.views import paginate
from core.models import Account, Repository
from core.views.decorators import check_account, check_support
from core.views.sort import get_repository_sort, get_account_sort
from private.forms import NoteForm, NoteDeleteForm, AccountTagsForm, TagsDeleteForm
from search.views import parse_keywords, make_query, RepositorySearchView

@check_account
def home(request, backend, slug, account=None):
    """
    Home page of an account
    """
    note = account.get_user_note()
    private_tags = account.get_user_tags()

    context = dict(
        note = note,
        account = account,
        private_tags = private_tags,
    )

    if 'edit_note' in request.GET:
        if not (request.user and request.user.is_authenticated()):
            messages.error(request, 'You must bo logged in to add/edit/delete your notes')
            return redirect(account)

        context['note_form'] = NoteForm(instance=note) if note else NoteForm(noted_object=account)
        if note:
            context['note_delete_form'] = NoteDeleteForm(instance=note)

    elif 'edit_tags' in request.GET:
        if not (request.user and request.user.is_authenticated()):
            messages.error(request, 'You must bo logged in to add/edit/delete your tags')
            return redirect(account)

        context['tags_form'] = AccountTagsForm(tagged_object=account)
        if private_tags:
            context['tags_delete_form'] = TagsDeleteForm(tagged_object=account)


    return render(request, 'core/accounts/home.html', context)


@check_support('user_followers')
@check_account
def followers(request, backend, slug, account=None):
    """
    Page listing accounts following an account
    """

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    sorted_followers = Account.for_list.filter(following=account)
    if sort['key']:
        sorted_followers = sorted_followers.order_by(sort['db_sort'])

    page = paginate(request, sorted_followers, settings.ACCOUNTS_PER_PAGE)

    return render(request, 'core/accounts/followers.html', dict(
        account = account,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))

@check_support('user_following')
@check_account
def following(request, backend, slug, account=None):
    """
    Page listing accounts followed by an account
    """

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    sorted_following = Account.for_list.filter(followers=account)
    if sort['key']:
        sorted_following = sorted_following.order_by(sort['db_sort'])

    page = paginate(request, sorted_following, settings.ACCOUNTS_PER_PAGE)

    return render(request, 'core/accounts/following.html', dict(
        account = account,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    ))

def _filter_repositories(request, account, queryset):
    """
    Helper doing all sort/query stuff about repositories, for listing
    repositories owned/followed or contributed by an account,
    """
    sort_key = request.GET.get('sort_by', 'name')
    repository_supports_owner = account.get_backend().supports('repository_owner')
    repository_supports_parent_fork = account.get_backend().supports('repository_parent_fork')
    sort = get_repository_sort(sort_key, repository_supports_owner)

    sorted_repositories = queryset.order_by(sort['db_sort'])

    if repository_supports_owner:
        owner_only = request.GET.get('owner-only', False) == 'y'
    else:
        owner_only = False

    if owner_only:
        sorted_repositories = sorted_repositories.filter(owner=account)

    if repository_supports_parent_fork:
        hide_forks = request.GET.get('hide-forks', False) == 'y'
    else:
        hide_forks = False

    if hide_forks:
        sorted_repositories = sorted_repositories.exclude(is_fork=True)

    query = request.GET.get('q')
    if query:
        keywords = parse_keywords(query)
        search_queryset = make_query(RepositorySearchView.search_fields, keywords)
        search_queryset = search_queryset.models(RepositorySearchView.model)
        if owner_only:
            search_queryset = search_queryset.filter(owner_id=account.id)
        if hide_forks:
            search_queryset = search_queryset.exclude(is_fork=True)
        # It's certainly not the best way to do it but.... :(
        sorted_ids = [r.id for r in sorted_repositories]
        if sorted_ids:
            search_queryset = search_queryset.filter(django_id__in=sorted_ids)
            found_ids = [int(r.pk) for r in search_queryset]
            sorted_repositories = [r for r in sorted_repositories if r.id in found_ids]

    distinct = request.GET.get('distinct', False) == 'y'
    if distinct and not owner_only:
        # try to keep one entry for each slug
        uniq = []
        slugs = {}
        for repository in sorted_repositories:
            if repository.slug in slugs:
                slugs[repository.slug].append(repository)
                continue
            slugs[repository.slug] = []
            uniq.append(repository)
        for repository in uniq:
            repository.distinct_others = slugs[repository.slug]
        # try to keep the first non-fork for each one
        sorted_repositories = []
        sort_lambda = lambda r:r.official_created
        for repository in uniq:
            if not repository.distinct_others or repository.owner_id == account.id:
                good_repository = repository
            else:
                important_ones = [r for r in repository.distinct_others if not r.is_fork]
                owned = [r for r in important_ones if r.owner_id == account.id]
                if owned:
                    good_repository = owned[0]  # only one possible
                else:
                    if important_ones:
                        if not repository.is_fork:
                            important_ones + [repository,]
                    else:
                        important_ones = repository.distinct_others + [repository,]

                    good_repository = sorted(important_ones, key=sort_lambda)[0]

                if good_repository != repository:
                    good_repository.distinct_others = [r for r in repository.distinct_others + [repository,] if r != good_repository]
                    delattr(repository, 'distinct_others')

                if hasattr(good_repository, 'distinct_others'):
                    good_repository.distinct_others = sorted(good_repository.distinct_others, key=sort_lambda)

            sorted_repositories.append(good_repository)

    page = paginate(request, sorted_repositories, settings.REPOSITORIES_PER_PAGE)

    return dict(
        account = account,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        owner_only = 'y' if owner_only else False,
        hide_forks = 'y' if hide_forks else False,
        distinct = 'y' if distinct else False,
        query = query or "",
    )

@check_support('user_repositories')
@check_account
def repositories(request, backend, slug, account=None):
    """
    Page listing repositories owned/watched by an account
    """
    queryset = Repository.for_list.filter(followers=account)
    context = _filter_repositories(request, account, queryset)
    return render(request, 'core/accounts/repositories.html', context)


@check_support('repository_contributors')
@check_account
def contributing(request, backend, slug, account=None):
    """
    Page listing repositories with contributions by an account
    """
    queryset = Repository.for_list.filter(contributors=account)
    context = _filter_repositories(request, account, queryset)
    return render(request, 'core/accounts/contributing.html', context)

