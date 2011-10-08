import re
import unicodedata

from django.utils.encoding import smart_unicode

from django_globals import globals

RE_SLUG = re.compile('[^\w-]')

def slugify(value):
    if not isinstance(value, unicode):
        value = smart_unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').lower()
    return RE_SLUG.sub('-', value).replace('_', '-')


def get_user_accounts():
    if not hasattr(globals, 'accounts'):
        if globals.user and globals.user.is_authenticated():
                globals.accounts = globals.user.accounts.all()
        else:
            globals.accounts = []
    return globals.accounts
