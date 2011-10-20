import random
import time

from redisco import models

def manager_get_random(self, **kwargs):
    """
    Add a method for the redisco Manager to return a rendomly picked object
    Must be used directly from objects (no filter or exclude)
    """
    token_list = self.filter(**kwargs)
    if not token_list:
        return None
    return random.choice(token_list)
models.managers.Manager.get_random = manager_get_random

class AccessToken(models.Model):
    """
    Model to store, in redis (via redisco) all tokens and their status
    """
    uid = models.Attribute(required=True, indexed=True, unique=True)
    login = models.Attribute(required=True, indexed=True)
    token = models.Attribute(required=True, indexed=True)
    backend = models.Attribute(required=True, indexed=True)
    status = models.IntegerField(required=True, indexed=True, default=200)
    using = models.BooleanField(required=True, indexed=True, default=False)
    last_use = models.DateTimeField(auto_now_add=True, auto_now=True)
    last_message = models.Attribute()

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return self.uid

    def is_valid(self):
        """
        Overrive the default method to save the uid, which is unique (by
        concatenating backend and token)
        """
        self.uid = '%s:%s:%s' % (self.backend, self.login, self.token)
        return super(AccessToken, self).is_valid()

    def lock(self):
        """
        Set the token as currently used
        """
        self.using = True
        self.save()

    def release(self):
        """
        Set the token as not currently used
        """
        self.using = False
        self.save()

    def set_status(self, code, message):
        """
        Set a new status and message for this token
        """
        self.status = code
        self.last_message = message
        self.save()


class AccessTokenManager(object):

    by_backend = {}

    @classmethod
    def get_for_backend(cls, backend_name):
        """
        Return a manager for the given backend name.
        Only one manager exists for each backend
        """
        if backend_name not in cls.by_backend:
            cls.by_backend[backend_name] = cls(backend_name)
        return cls.by_backend[backend_name]

    def __init__(self, backend_name):
        self.backend_name = backend_name

    def get_one(self, default_token=None, wait=True):
        """
        Return an available token for the current backend and lock it
        If `default_token` is given, check it's a good one
        """
        token = None
        if default_token:
            if default_token.using or default_token.status != 200:
                token = None
            else:
                token = default_token

        while not token:
            token = AccessToken.objects.get_random(
                backend = self.backend_name,
                using   = False,
                status  = 200
            )
            if not token:
                if not wait:
                    break
                time.sleep(0.5)

        if token:
            token.lock()
        return token

    def get_for_account(self, account):
        """
        Return the token for the given account
        """
        if not account.access_token:
            return None
        return AccessToken.objects.filter(
            backend = self.backend_name,
            login = account.slug,
            token = account.access_token,
        ).first()

    def get_by_uid(self, uid):
        """
        Return the token for a given uid
        """
        if not uid:
            return None
        return AccessToken.objects.filter(backend=self.backend_name, uid=uid).first()
