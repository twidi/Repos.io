# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from httplib import responses


SPECIFIC_ERROR_CODES = {
    'SUSPENDED': 99403,
}

class CoreException(Exception):
    pass


class InvalidIdentifiersForProject(CoreException):
    def __init__(self, backend, message=None):
        super(InvalidIdentifiersForProject, self).__init__(
            message or 'Invalid identifiers for the project. The %s backend says that you need %s' %
            (
                backend.name,
                backend.needed_repository_identifiers,
            )
        )


class OriginalProviderLoginMissing(CoreException):
    def __init__(self, user, backend_name, message=None):
        super(OriginalProviderLoginMissing, self).__init__(
            message or 'The original_login from the %s backend for the user %s is required' %
            (
                backend_name,
                user
            )
        )


class BackendError(CoreException):
    def __init__(self, message=None, code=None, extra=None):
        if not message:
            if code and code in responses:
                message = 'An error prevent us to accomplish your request : %s' % responses[code]
            else:
                message = 'An undefined error prevent us to accomplish your request'
        super(BackendError, self).__init__(message)
        self.message = message
        self.code = code
        self.extra = extra or {}

    @staticmethod
    def make_for(backend_name, code=None, what=None, message=None, extra=None):

        if code == SPECIFIC_ERROR_CODES['SUSPENDED']:
            return BackendSuspendedTokenError(backend_name, what, message, extra)

        if code == 401:
            return BackendUnauthorizedError(backend_name, what, message, extra)

        if code == 403:
            return BackendForbiddenError(backend_name, what, message, extra)

        if code == 404:
            return BackendNotFoundError(backend_name, what, extra)

        elif 400 <= code < 500:
            return BackendAccessError(backend_name, what, code, message, extra)

        elif code >= 500:
            return BackendInternalError(backend_name, what, code, message, extra)

        return BackendError(message, code, extra)


class MultipleBackendError(BackendError):
    def __init__(self, exceptions):
        super(MultipleBackendError, self).__init__(
            'Many errors occurred : ' + ', '.join([str(e) for e in exceptions]))
        self.exceptions = exceptions


class BackendNotFoundError(BackendError):
    def __init__(self, backend_name, what, extra=None):
        super(BackendNotFoundError, self).__init__(
            '%s cannot be found on %s' % (what, backend_name), 404, extra)


class BackendAccessError(BackendError):
    def __init__(self, backend_name, what, code, message=None, extra=None):
        super(BackendAccessError, self).__init__(
            '%s cannot be accessed on %s: %s' % (what, backend_name, message), code, extra)


class BackendForbiddenError(BackendAccessError):
    def __init__(self, backend_name, what, message=None, extra=None):
        super(BackendForbiddenError, self).__init__(
            backend_name, what, 403, message or 'access forbidden', extra)


class BackendUnauthorizedError(BackendAccessError):
    def __init__(self, backend_name, what, message=None, extra=None):
        super(BackendUnauthorizedError, self).__init__(
            backend_name, what, 401, message or 'unauthorized access', extra)


class BackendInternalError(BackendError):
    def __init__(self, backend_name, what, code, message=None, extra=None):
        super(BackendInternalError, self).__init__(
            '%s cannot be accessed because %s encountered an internal error: %s' % (
                what, backend_name, message or '(no more info)'), code, extra)


class BackendSuspendedTokenError(BackendError):
    def __init__(self, backend_name, what, code, message=None, extra=None):
        super(BackendSuspendedTokenError, self).__init__(
            '%s cannot be accessed on %s because token is suspended: %s' % (
                what, backend_name, message or '(no more info)'), 403, extra)
