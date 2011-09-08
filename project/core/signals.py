from django.dispatch import receiver
from django.contrib import messages

from social_auth.signals import pre_update
from django_globals import globals

from core.backends import BACKENDS_BY_AUTH
from core.models import Account
from core.exceptions import BackendError

@receiver(pre_update, sender=None, dispatch_uid='core.signals.CreateAccountOnSocialAccount')
def CreateAccountOnSocialAccount(sender, user, response, details, **kwargs):
    """
    Associate (and then fetch if needed) an Account object for the user just logged
    """
    if not getattr(sender, 'name', None) in BACKENDS_BY_AUTH:
        return False

    if not getattr(user, 'social_user', False):
        return False

    if not user.pk:
        user.save()
    try:
        Account.objects.get_for_social_auth_user(user.social_user)
    except BackendError, e:
        messages.error(globals.request, e.message)
    except Exception:
        messages.error(globals.request, 'We were not able to associate your account !')

    return False

