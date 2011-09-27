from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect

from core.views.decorators import check_account, check_support
from core.views.sort import get_repository_sort, get_account_sort
from user_notes.forms import NoteForm, NoteDeleteForm
from search.views import parse_keywords, make_query, RepositorySearchView

@check_account
def home(request, backend, slug, account=None):
    """
    Home page of an account
    """
    note = account.get_user_note()

    context = dict(
        note = note,
        account = account,
    )

    if 'edit_note' in request.GET:
        if not (request.user and request.user.is_authenticated()):
            messages.error(request, 'You must bo logged in to add/edit/delete your notes')
            return redirect(account)

        context['note_form'] = NoteForm(instance=note) if note else NoteForm(noted_object=account)
        if note:
            context['note_delete_form'] = NoteDeleteForm(instance=note)


    return render(request, 'core/accounts/home.html', context)


@check_support('user_followers')
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

@check_support('user_following')
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

@check_support('user_repositories')
@check_account
def repositories(request, backend, slug, account=None):
    """
    Page listing repositories owned/watched by an account
    """

    sort_key = request.GET.get('sort_by', 'name')
    repository_supports_owner = account.get_backend().supports('repository_owner')
    repository_supports_parent_fork = account.get_backend().supports('repository_parent_fork')
    sort = get_repository_sort(sort_key, repository_supports_owner)

    sorted_repositories = account.repositories.order_by(sort['db_sort']).select_related('owner')

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

    return render(request, 'core/accounts/repositories.html', dict(
        account = account,
        sorted_repositories = sorted_repositories,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        owner_only = 'y' if owner_only else False,
        hide_forks = 'y' if hide_forks else False,
        query = query,
    ))

