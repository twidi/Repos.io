# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import template
register = template.Library()

@register.filter
def dict_get(dikt, key):
    """
    Custom template tag used like so:
    {{ dictionary|dict_get:var }}
    where dictionary is a dictionary and key is a variable representing
    one of it's keys
    """
    try:
        return dikt.__getitem__(key)
    except:
        return ''

@register.filter
def attr_get(obj, attr):
    """
    Custom template tag used like so:
    {{ object|attr_get:var }}
    where object is an object with attributes and attr is a variable representing
    one of it's attributes
    """
    try:
        result = getattr(obj, attr)
        if callable(result):
            return result()
        return result
    except:
        return ''

