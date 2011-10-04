from django import template
from django.contrib.contenttypes.models import ContentType

from django_globals import globals
from haystack.models import SearchResult
from notes.models import Note

from private.models import ALLOWED_MODELS

register = template.Library()

@register.simple_tag
def prepare_private(objects):
    """
    Update each object included in the `objects` with private informations (note and tags)
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

        user = globals.user

        # objects to manage
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)

        dict_objects = dict((int(obj.pk), obj) for obj in objects)
        keys = dict_objects.keys()

        # read and save notes
        notes = Note.objects.filter(
                content_type = content_type,
                author = user,
                object_id__in=keys
                ).values_list('object_id', 'rendered_content')

        for obj_id, note in notes:
            dict_objects[obj_id].has_note = True
            dict_objects[obj_id].rendered_note = note

        # read and save tags
        if model_name == 'account':
            qs_tags = user.tagging_privatetaggedaccount_items
        else:
            qs_tags = user.tagging_privatetaggedrepository_items

        private_tagged_items = qs_tags.filter(
                content_object__in=keys
            ).values_list('content_object', 'tag__name')

        for obj_id, tag in private_tagged_items:
            if not getattr(dict_objects[obj_id], 'has_private_tags'):
                dict_objects[obj_id].has_private_tags = True
                dict_objects[obj_id].private_tags = []
            dict_objects[obj_id].private_tags.append(tag)

        return ''
    except:
        return ''

