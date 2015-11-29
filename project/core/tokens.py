# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from datetime import datetime
import time

from redisco import models, connection

from utils import now_timestamp

AVAILABLE_LIST_KEY = 'available_tokens'


class AccessToken(models.Model):
    """
    Model to store, in redis (via redisco) all tokens and their status
    """
    uid = models.Attribute(required=True, indexed=True, unique=True)
    login = models.Attribute(required=True, indexed=True)
    token = models.Attribute(required=True, indexed=True)
    backend = models.Attribute(required=True, indexed=True)
    status = models.IntegerField(required=True, indexed=True, default=200)
    last_use = models.DateTimeField()
    last_message = models.Attribute()
    suspended_until = models.DateTimeField()

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return self.uid

    def save(self):
        is_new = self.is_new()
        self.last_use = datetime.utcnow()
        result = super(AccessToken, self).save()
        if result is True and is_new:
            self.release()
        return result

    def is_valid(self):
        """
        Override the default method to save the uid, which is unique (by
        concatenating backend and token)
        """
        self.uid = '%s:%s:%s' % (self.backend, self.login, self.token)
        return super(AccessToken, self).is_valid()

    def lock(self):
        """
        Set the token as currently used
        """
        return connection.srem(AVAILABLE_LIST_KEY, self.uid)

    def release(self):
        """
        Set the token as not currently used
        """
        return connection.sadd(AVAILABLE_LIST_KEY, self.uid)

    def set_status(self, code, message):
        """
        Set a new status and message for this token
        """
        self.status = code
        self.last_message = message
        self.save()

    def suspend(self, suspended_until=None, message=None):
        """
        Suspend the token until the given utc timestamp
        """
        if suspended_until:
            self.suspended_until = datetime.utcfromtimestamp(suspended_until)
        else:
            self.suspended_until = None
        self.last_message = message
        self.save()

        if suspended_until:
            # We make the `suspended_until` key auto expire
            key = self.key('suspended_until')
            connection.expire(key, round(suspended_until - now_timestamp()) + 1)


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
        """
        A manager is for a specific backend
        """
        self.backend_name = backend_name

    def get_one(self, default_token=None, wait=True):
        """
        Return an available token for the current backend and lock it
        If `default_token` is given, check it's a good one
        """
        if default_token:
            default_token = self.get_by_uid(default_token.uid)
            if default_token and default_token.status == 200 and not default_token.suspended_until:
                if default_token.lock():
                    return default_token

        while True:
            uid = connection.spop(AVAILABLE_LIST_KEY)
            token = self.get_by_uid(uid)
            if token and token.status == 200 and not token.suspended_until:
                return token

            if not wait:
                return None

            time.sleep(0.5)

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
