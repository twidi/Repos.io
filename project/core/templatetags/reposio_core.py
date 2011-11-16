from django import template

from core.backends import BaseBackend, get_backend
from tagging.flags import split_tags_and_flags

register = template.Library()

@register.filter
def supports(backend, functionnality):
    """
    Return True if the given backend supports the given functionnality.
    `backend` can be a backend name, or a backend object
    """

    if isinstance(backend, basestring):
        backend = get_backend(backend)
        if not backend:
            return False

    if isinstance(backend, BaseBackend):
        return backend.supports(functionnality)

    return False

@register.filter
def links_with_user(obj, user):
    """
    Return informations about some links between the given object (account or repository) and the given user
    """
    try:
        return obj.links_with_user(user)
    except:
        return {}

@register.filter
def note_and_tags(obj, user):
    """
    Return the note and tags for the given object (account or repository) by the given user
    """
    try:
        note = obj.get_user_note(user)
        private_tags = obj.get_user_tags(user)
        if private_tags:
            flags_and_tags = split_tags_and_flags(private_tags)
        else:
            flags_and_tags = None

        return dict(
            note = note,
            flags_and_tags = flags_and_tags
        )
    except:
        return {}
