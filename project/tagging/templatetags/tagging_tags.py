from django import template

from utils.model_utils import get_app_and_model
from tagging.models import PublicTaggedAccount, PublicTaggedRepository

register = template.Library()

@register.simple_tag
def prepare_public_tags(objects):
    """
    Retrieve public tags for all objects
    """

    try:
        # find objects' type
        obj = objects[0]

        model_name = '%s.%s' % get_app_and_model(obj)

        if model_name == 'core.account':
            tag_model = PublicTaggedAccount
        elif model_name == 'core.repository':
            tag_model = PublicTaggedRepository
        else:
            return ''

        dict_objects = dict((int(obj.pk), obj) for obj in objects)
        ids = sorted(dict_objects.keys())

        items = tag_model.objects.filter(content_object__in=ids).select_related('tag')
        for item in items:
            if item.content_object_id not in dict_objects:
                continue
            obj = dict_objects[item.content_object_id]
            if not hasattr(obj, 'prepared_public_tags'):
                obj.prepared_public_tags = []
            obj.prepared_public_tags.append(item.tag)

        return ''

    except:
        return ''
