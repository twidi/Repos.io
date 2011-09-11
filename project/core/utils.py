import re

from django.template.defaultfilters import slugify as base_slugify

RE_SLUG = re.compile('[^\w\s-]')

def slugify(value):
    return base_slugify(RE_SLUG.sub('-', value)).replace('_', '-')




