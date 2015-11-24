# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf import settings as django_settings

from core.backends import BACKENDS_BY_AUTH
from core.core_utils import get_user_accounts


def backends(request):
    return dict(
        backends_map = dict((backend.name, auth_backend) for auth_backend, backend in BACKENDS_BY_AUTH.items())
    )


def objects(request):
    return dict(
        user_accounts = get_user_accounts()
    )


def settings(request):
    return dict(
        INDEX_ACTIVATED=django_settings.INDEX_ACTIVATED
    )
