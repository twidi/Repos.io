from django import template
from django.contrib.contenttypes.models import ContentType

from django_globals import globals
from haystack.models import SearchResult
from notes.models import Note

from user_notes.models import ALLOWED_MODELS

register = template.Library()

@register.simple_tag
def prepare_notes(objects):
    """
    Update each object included in the `objects` with a `has_note` attribute
    All objects must be from the same content_type
    """
    try:
        if not (globals.user and globals.user.is_authenticated()):
            raise
        obj = objects[0]

        if isinstance(obj, SearchResult):
            app_label, model_name = obj.app_label, obj.model_name
        else:
            app_label, model_name = obj._meta.app_label, obj._meta.module_name

        if '%s.%s' % (app_label, model_name) not in ALLOWED_MODELS:
            raise

        content_type = ContentType.objects.get(app_label=app_label, model=model_name)

        dict_objects = dict((obj.pk, obj) for obj in objects)

        ids_with_note = Note.objects.filter(
                content_type = content_type,
                author = globals.user,
                object_id__in=dict_objects.keys()
                ).values_list('object_id', flat=True)

        for obj_id in list(ids_with_note):
            dict_objects[obj_id].has_note = True

        return ''
    except:
        return ''

