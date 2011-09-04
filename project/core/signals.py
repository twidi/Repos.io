from django.db.models.signals import post_save
from django.dispatch import receiver

from social_auth.models import UserSocialAuth

from core.models import Account

@receiver(post_save, sender=UserSocialAuth, dispatch_uid='core.signals.CreateAccountOnSocialAccount')
def CreateAccountOnSocialAccount(sender, **kwargs):
    """
    Associate (and then fetch if needed) an Account object for the user just logged
    """
    if sender != UserSocialAuth:
        return
    instance = kwargs['instance']
    if instance.pk and instance.extra_data:
        try:
            Account.objects.get_for_social_auth_user(instance)
        except:
            pass




