import re
import unicodedata

from django.utils.encoding import smart_unicode

RE_SLUG = re.compile('[^\w\s-]')

def slugify(value):
    if not isinstance(value, unicode):
        value = smart_unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').lower()
    return RE_SLUG.sub('-', value).replace('_', '-')




