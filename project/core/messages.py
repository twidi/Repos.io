from django.contrib.messages import constants as levels
from django.contrib.auth.models import User

from offline_messages import utils as messages_utils

def get_user(user):
    """
    Try to return a User, the parameter can be:
    - a User object
    - a user id
    - a user id as a string
    - a username
    """
    if not user:
        return None
    if isinstance(user, User):
        return user
    try:
        if isinstance(user, basestring):
            if user.isdigit():
                user = int(user)
            else:
                return User.objects.get(username=user)
        if isinstance(user, int):
            return User.objects.get(id=user)
    except:
        return None

def add_message(user, level, message, content_object=None, meta={}):
    user = get_user(user)
    if not user:
        return None
    return messages_utils.create_offline_message(user, message, level, content_object=content_object, meta=meta)

def debug(user, message, **kwargs):
    return add_message(user, levels.DEBUG, message, **kwargs)

def info(user, message, **kwargs):
    return add_message(user, levels.INFO, message, **kwargs)

def success(user, message, **kwargs):
    return add_message(user, levels.SUCCESS, message, **kwargs)

def error(user, message, **kwargs):
    return add_message(user, levels.ERROR, message, **kwargs)

