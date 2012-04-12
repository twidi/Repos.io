# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from operator import itemgetter
from copy import copy

from django import template

register = template.Library()

@register.filter
def tag_is_in(tag, tags):
    """
    Return True if `tag` is in the given list
    """
    if not tag or not tags:
        return False

    if isinstance(tag, dict):
        slug = tag['slug']
    else:
        slug = tag.slug

    if isinstance(tags[0], dict):
        return slug in [t['slug'] for t in tags]
    else:
        return slug in [t.slug for t in tags]

#def tags_as_dicts(tags):
#    if not tags:
#        return []
#    if isinstance(tags[0], dict):
#        return copy(tags)
#    else:
#        result = []
#        for tag in tags:
#            tag_dict = dict(slug=tag.slug, name=tag.name)
#            if hasattr(tag, 'for_only'):
#                tag_dict['for_only'] = tag.for_only
#            result.append(tag_dict)
#        return result

@register.filter
def add_tags(tags1, tags2):

    if not tags2:
        return tags1 or []

    if not tags1:
        return tags2

    tags1 = copy(tags1)
    tags2 = sorted([dict(slug=t.slug, name=t.name) for t in tags2], key=itemgetter('slug'))

    # try to do it fast...
    result = []
    while tags1:
        while tags2 and tags2[0]['slug'] <= tags1[0]['slug']:
            tag = tags2.pop(0)
            if tag['slug'] != tags1[0]['slug']:
                result.append(tag)
        if not tags2:
            break
        result.append(tags1.pop(0))
    result += tags1

    return result
