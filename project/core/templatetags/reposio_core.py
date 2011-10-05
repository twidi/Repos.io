from django import template

from core.backends import BaseBackend, get_backend
from core.models import Account, Repository

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
