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

    social_user = None
    try:
        social_users = user.social_auth.all()
        for soc_user in social_users:
            if details['username'] == soc_user.extra_data.get('original_login'):
                social_user = soc_user
                break
    except:
        pass

    try:
        if not social_user:
            raise Exception('Social user not found')
        Account.objects.associate_to_social_auth_user(social_user)
    except BackendError, e:
        messages.error(globals.request, e.message)
    except Exception:
        messages.error(globals.request, 'We were not able to associate your account !')

    return False

