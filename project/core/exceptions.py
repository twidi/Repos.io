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
    def make_for(backend_name, code=None, what=None):

        if code == 401:
            return BackendUnauthorizedError(backend_name, what)

        if code == 403:
            return BackendForbiddenError(backend_name, what)

        if code == 404:
            return BackendNotFoundError(backend_name, what)

        elif code >= 400 and code < 500:
            return BackendAccessError(code, backend_name, what)

        elif code >= 500:
            return BackendInternalError(code, backend_name, what)

        return BackendError(message=None, code=None)

class MultipleBackendError(BackendError):
    def __init__(self, messages):
        super(MultipleBackendError, self).__init__(
            'Many errors occured : ' + ', '.join(messages))
        self.messages = messages

class BackendNotFoundError(BackendError):
    def __init__(self, backend_name, what):
        super(BackendNotFoundError, self).__init__(
            '%s cannot be found on %s' % (what, backend_name), 404)

class BackendAccessError(BackendError):
    def __init__(self, code, message, backend_name, what):
        super(BackendAccessError, self).__init__(
            '%s cannot be accessed on %s: %s' % (what, backend_name, message), code)

class BackendForbiddenError(BackendAccessError):
    def __init__(self, backend_name, what):
        super(BackendForbiddenError, self).__init__(
                403, 'access forbidden', backend_name, what)


class BackendUnauthorizedError(BackendAccessError):
    def __init__(self, backend_name, what):
        super(BackendUnauthorizedError, self).__init__(
                401, 'unauthorized access', backend_name, what)

class BackendInternalError(BackendError):
    def __init__(self, code, backend_name, what):
        super(BackendError, self).__init__(
            '%s cannot be accessed because %s encountered an internal error' % (what, backend_name), code)

