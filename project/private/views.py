from django_globals import globals
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseNotAllowed

from notes.models import Note

from private.forms import (NoteForm, NoteDeleteForm,
        TagsForm, TagsDeleteForm, TagsAddOneForm, TagsRemoveOneForm, TagsCreateOneForm)
from utils.model_utils import get_app_and_model

def get_user_note_for_object(obj):
    """
    Return a note by the current logged user for the given object
    A user can only have one note by object
    """
    user = globals.user
    if not (user and user.is_authenticated()):
        return None

    app_label, model_name = get_app_and_model(obj)

    notes = Note.objects.filter(
        author=user,
        content_type__app_label = app_label,
        content_type__model = model_name,
        object_id=obj.id
    )
    if notes:
        return notes[0]

    return None

def redirect_from_editor(request, default):
    """
    Manage redirect when we came from the editor.
    If the used clicked a button named "submit-close", he wants to
    quit the editor after action done, so redirect to the `when_finished`
    url, else use the `edit_url`.
    If not from the editor, redirect to the object default page.
    """
    param_name = 'edit_url'
    if request.POST.get('submit-close'):
        param_name = 'when_finished'
    return redirect(request.POST.get(param_name) or default)

@require_POST
@login_required
def note_save(request):
    """
    Save a note for the current user
    """
    form = NoteForm(request.POST)
    if form.is_valid():
        noted_object = form.save().content_object
        messages.success(request, 'Your private note was saved')
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseNotAllowed('Vilain :)')
        messages.error(request, 'We were unable to save your note !')

    return redirect_from_editor(request, noted_object)


@require_POST
@login_required
def note_delete(request):
    """
    Delete a note for the current user
    """
    form = NoteDeleteForm(request.POST)
    if form.is_valid():
        noted_object = form.get_related_object()
        form.save()
        messages.success(request, 'Your private note was deleted')
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseNotAllowed('Vilain :)')
        messages.error(request, 'We were unable to delete your note !')

    return redirect_from_editor(request, noted_object)


def get_user_tags_for_object(obj):
    """
    Return all tags associated to an object by the current logged user
    """
    user = globals.user
    if not (user and user.is_authenticated()):
        return None

    return obj.all_private_tags(user)


@require_POST
@login_required
def tags_save(request):
    """
    Save some tags for the current user
    """
    view_data = dict(
        save = dict(
            form = TagsForm,
            success = 'Your private tags were saved',
            error = 'We were unable to save your tags !',
        ),
        add = dict(
            form = TagsAddOneForm,
            success = 'Your private tags was added',
            error = 'We were unable to add your tag !',
        ),
        remove = dict(
            form = TagsRemoveOneForm,
            success = 'Your private tags was removed',
            error = 'We were unable to remove your tag !',
        ),
        create = dict(
            form = TagsCreateOneForm,
            success = 'Your private tags was added',
            error = 'We were unable to add your tag !',
        ),
    )

    action = request.POST.get('act', 'save')

    form = view_data[action]['form'](request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, view_data[action]['success'])
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseNotAllowed('Vilain :)')
        messages.error(request, view_data[action]['error'])

    return redirect_from_editor(request, tagged_object)

@require_POST
@login_required
def tags_delete(request):
    """
    Delete some tags for the current user
    """
    form = TagsDeleteForm(request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, 'Your private tags were deleted')
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseNotAllowed('Vilain :)')
        messages.error(request, 'We were unable to delete your tags !')

    return redirect_from_editor(request, tagged_object)
