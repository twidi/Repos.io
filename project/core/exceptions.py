# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from httplib import responses


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
    def __init__(self, message=None, code=None):
        if not message:
            if code and code in responses:
                message = 'An error prevent us to accomplish your request : %s' % responses[code]
            else:
                message = 'An undefined error prevent us to accomplish your request'
        super(BackendError, self).__init__(message)
        self.message = message
        self.code = code

    @staticmethod
    def make_for(backend_name, code=None, what=None, message=None):

        if code == 401:
            return BackendUnauthorizedError(backend_name, what, message)

        if code == 403:
            return BackendForbiddenError(backend_name, what, message)

        if code == 404:
            return BackendNotFoundError(backend_name, what)

        elif 400 <= code < 500:
            return BackendAccessError(backend_name, what, code, message)

        elif code >= 500:
            return BackendInternalError(backend_name, what, code, message)

        return BackendError(message, code)


class MultipleBackendError(BackendError):
    def __init__(self, messages):
        super(MultipleBackendError, self).__init__(
            'Many errors occurred : ' + ', '.join(messages))
        self.messages = messages


class BackendNotFoundError(BackendError):
    def __init__(self, backend_name, what):
        super(BackendNotFoundError, self).__init__(
            '%s cannot be found on %s' % (what, backend_name), 404)


class BackendAccessError(BackendError):
    def __init__(self, backend_name, what, code, message=None):
        super(BackendAccessError, self).__init__(
            '%s cannot be accessed on %s: %s' % (what, backend_name, message), code)


class BackendForbiddenError(BackendAccessError):
    def __init__(self, backend_name, what, message=None):
        super(BackendForbiddenError, self).__init__(
            backend_name, what, 403, message or 'access forbidden')


class BackendUnauthorizedError(BackendAccessError):
    def __init__(self, backend_name, what, message=None):
        super(BackendUnauthorizedError, self).__init__(
            backend_name, what, 401, message or 'unauthorized access')


class BackendInternalError(BackendError):
    def __init__(self, backend_name, what, code, message=None):
        super(BackendError, self).__init__(
            '%s cannot be accessed because %s encountered an internal error: %s' % (
                what, backend_name, message or '(no more info)'), code)
