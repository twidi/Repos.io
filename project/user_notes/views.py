from django_globals import globals
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseNotAllowed

from notes.models import Note

from user_notes.forms import NoteForm

def get_user_note_for_object(obj):
    """
    Return a note by the current logged user for the given object
    A user can only have one note by object
    """
    user = globals.user
    if not user:
        return None

    obj_type = ContentType.objects.get_for_model(obj)
    notes = Note.objects.filter(author=user,
                content_type__pk=obj_type.id, object_id=obj.id)
    if notes:
        return notes[0]

    return None

@require_POST
@login_required
def save(request):
    """
    Save a note for the current user
    """
    form = NoteForm(request.POST)
    if form.is_valid():
        noted_object = form.save().content_object
        messages.success(request, 'Your private note was saved')
    else:
        noted_object = form.get_noted_object()
        if not noted_object:
            return HttpResponseNotAllowed('Vilain :)')
        messages.error(request, 'We were unable to save your note !')

    return redirect(noted_object)
