from django.shortcuts import render

from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort
from user_notes.forms import NoteForm

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    note = repository.get_user_note()

    context = dict(
        note = note,
        repository = repository,
    )

    if 'edit_note' in request.GET:
        context['note_form'] = NoteForm(instance=note) if note else NoteForm(noted_object=repository)

    return render(request, 'core/repositories/home.html', context)

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
