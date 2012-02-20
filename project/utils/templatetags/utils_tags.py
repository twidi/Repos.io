# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from uuid import uuid4

from django.utils.safestring import mark_safe
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

def insert_if(value, test, html):
    """
    Return the html if the value is equal to the tests
    """
    try:
        if value == test:
            return mark_safe(html)
    except:
        pass
    return ''

@register.filter
def check_if(value, test):
    return insert_if(value, test, ' checked="checked"')

@register.filter
def select_if(value, test):
    return insert_if(value, test, ' selected="selected"')

@register.filter
def current_if(value, test):
    return insert_if(value, test, ' current')

@register.filter
def current_class_if(value, test):
    return insert_if(value, test, ' class="current"')

class NoneIfOnlySpaces(template.Node):
    """
    If we have only spaces in the block, return an empty string
    """
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        content = self.nodelist.render(context)
        if content.strip() == '':
            return ''
        return content

def do_none_if_only_spaces(parser, token):
    nodelist = parser.parse(('end_%s' % token.contents,))
    parser.delete_first_token()
    return NoneIfOnlySpaces(nodelist)

register.tag('none_if_only_spaces', do_none_if_only_spaces)


# http://www.nomadjourney.com/2009/03/uuid-template-tag-for-django/
class UUIDNode(template.Node):
    """
    Implements the logic of this tag.
    """
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = str(uuid4())
        return ''

def do_uuid(parser, token):
    """
    The purpose of this template tag is to generate a random
    UUID and store it in a named context variable.

    Sample usage:
        {% uuid var_name %}
        var_name will contain the generated UUID
    """
    try:
        tag_name, var_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument" % token.contents.split()[0]
    return UUIDNode(var_name)

do_uuid = register.tag('uuid', do_uuid)

