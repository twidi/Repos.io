from django import template

from core.backends import BaseBackend, get_backend

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

