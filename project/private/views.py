# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django_globals import globals
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import HttpResponseBadRequest

from notes.models import Note

from private.forms import (NoteForm, NoteDeleteForm,
        TagsForm, TagsDeleteForm, TagsAddOneForm, TagsRemoveOneForm, TagsCreateOneForm)
from utils.model_utils import get_app_and_model
from core.models import get_object_from_str

def get_user_note_for_object(obj, user=None):
    """
    Return a note by the current logged user for the given object
    A user can only have one note by object
    """
    user = user or globals.user
    if not (user and user.is_authenticated()):
        return None

    app_label, model_name = get_app_and_model(obj)

    try:
        return Note.objects.filter(
            author=user,
            content_type__app_label = app_label,
            content_type__model = model_name,
            object_id=obj.id
        )[0]
    except:
        return None

def return_from_editor(request, obj):
    """
    Manage redirect when we came from the editor.
    If the used clicked a button named "submit-close", he wants to
    quit the editor after action done, so redirect to the `when_finished`
    url, else use the `edit_url`.
    If not from the editor, redirect to the object default page.
    """
    if request.is_ajax():
        context = dict(
            obj_type = get_app_and_model(obj)[1],
            object = obj,
            edit_extra = obj.simple_str(),
            want_close = bool(request.POST.get('submit-close')),
        )
        return render(request, 'private/edit_private_ajax.html', context)

    param_name = 'edit_url'
    if request.POST.get('submit-close'):
        param_name = 'when_finished'
    return redirect(request.POST.get(param_name) or obj)

def ajax_edit(request, object_key):
    """
    Render the edit form, without other html, for use in ajax
    """
    return render(request, 'private/edit_private_ajax.html', dict(edit_extra = object_key))

def ajax_close(request, object_key):
    """
    Render the html to replace existing when closing via ajax the private editor
    """
    obj = get_object_from_str(object_key)
    return render(request, 'private/edit_private_ajax_onclose.html', dict(
        obj_type = get_app_and_model(obj)[1],
        object = obj,
    ))


@require_POST
@login_required
def note_save(request):
    """
    Save a note for the current user
    """
    if not request.POST.get('content'):
        return note_delete(request)

    form = NoteForm(request.POST)
    if form.is_valid():
        noted_object = form.save().content_object
        messages.success(request, 'Your private note was saved')
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, 'We were unable to save your note !')

    return return_from_editor(request, noted_object)


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
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, 'We were unable to delete your note !')

    return return_from_editor(request, noted_object)


def get_user_tags_for_object(obj, user=None):
    """
    Return all tags associated to an object by the current logged user
    """
    user = user or globals.user
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
            error = 'We were unable to add your tag ! (you must provide one...)',
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
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, view_data[action]['error'])

    return return_from_editor(request, tagged_object)

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
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, 'We were unable to delete your tags !')

    return return_from_editor(request, tagged_object)
