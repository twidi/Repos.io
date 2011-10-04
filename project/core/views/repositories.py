from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect

from core.views.decorators import check_repository, check_support
from core.views.sort import get_account_sort
from private.forms import NoteForm, NoteDeleteForm, RepositoryTagsForm, TagsDeleteForm

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    note = repository.get_user_note()
    private_tags = repository.get_user_tags()

    context = dict(
        note = note,
        repository = repository,
        private_tags = private_tags,
    )

    if 'edit_note' in request.GET:
        if not (request.user and request.user.is_authenticated()):
            messages.error(request, 'You must bo logged in to add/edit/delete your notes')
            return redirect(repository)

        context['note_form'] = NoteForm(instance=note) if note else NoteForm(noted_object=repository)
        if note:
            context['note_delete_form'] = NoteDeleteForm(instance=note)

    elif 'edit_tags' in request.GET:
        if not (request.user and request.user.is_authenticated()):
            messages.error(request, 'You must bo logged in to add/edit/delete your tags')
            return redirect(repository)

        context['tags_form'] = RepositoryTagsForm(tagged_object=repository)
        if private_tags:
            context['tags_delete_form'] = TagsDeleteForm(tagged_object=repository)

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
