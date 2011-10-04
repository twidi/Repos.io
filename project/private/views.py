from django_globals import globals
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseNotAllowed

from notes.models import Note

from private.forms import NoteForm, NoteDeleteForm, TagsForm, TagsDeleteForm

def get_user_note_for_object(obj):
    """
    Return a note by the current logged user for the given object
    A user can only have one note by object
    """
    user = globals.user
    if not (user and user.is_authenticated()):
        return None

    obj_type = ContentType.objects.get_for_model(obj)
    notes = Note.objects.filter(author=user,
                content_type__pk=obj_type.id, object_id=obj.id)
    if notes:
        return notes[0]

    return None


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

    return redirect(noted_object)


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

    return redirect(noted_object)


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
    form = TagsForm(request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, 'Your private tags were saved')
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseNotAllowed('Vilain :)')
        messages.error(request, 'We were unable to save your tags !')

    return redirect(tagged_object)

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

    return redirect(tagged_object)
