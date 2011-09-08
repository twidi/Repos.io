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
    def make_for(backend_name, code=None, object_type=None, object_name=None):

        if code == 401:
            if object_type == 'account':
                return BackendAccountUnauthorizedError(backend_name, object_name)
            elif object_type == 'repository':
                return BackendRepositoryUnauthorizedError(backend_name, object_name)
            return BackendUnauthorizedError()

        if code == 403:
            if object_type == 'account':
                return BackendAccountForbiddenError(backend_name, object_name)
            elif object_type == 'repository':
                return BackendRepositoryForbiddenError(backend_name, object_name)
            return BackendForbiddenError()

        if code == 404:
            if object_type == 'account':
                return BackendAccountNotFoundError(backend_name, object_name)
            elif object_type == 'repository':
                return BackendRepositoryNotFoundError(backend_name, object_name)
            return BackendNotFoundError()

        elif code >= 400 and code < 500:
            return BackendAccessError(code=code)

        elif code >= 500:
            return BackendInternalError(code=code)

        return BackendError(message=None, code=None)

class BackendNotFoundError(BackendError):
    def __init__(self, message=None):
        super(BackendNotFoundError, self).__init__(
            message or 'The wanted object was not found', 404)

class BackendAccountNotFoundError(BackendNotFoundError):
    def __init__(self, backend_name, account_name):
        super(BackendAccountNotFoundError, self).__init__(
            '`%s` account not found on %s' % (
                account_name, backend_name)
        )

class BackendRepositoryNotFoundError(BackendNotFoundError):
    def __init__(self, backend_name, repository_name):
        super(BackendRepositoryNotFoundError, self).__init__(
            '`%s` repository not found on %s' % (
                repository_name, backend_name)
        )

class BackendAccessError(BackendError):
    def __init__(self, message=None, code=None):
        super(BackendAccessError, self).__init__(
            message or 'The wanted access cannot be done', code)
    pass

class BackendForbiddenError(BackendAccessError):
    def __init__(self, message=None):
        super(BackendForbiddenError, self).__init__(
            message or 'The wanted access is forbidden', 403)

class BackendAccountForbiddenError(BackendForbiddenError):
    def __init__(self, backend_name, account_name):
        super(BackendAccountForbiddenError, self).__init__(
            '`%s` access if forbidden by %s' % (
                account_name, backend_name)
        )

class BackendRepositoryForbiddenError(BackendForbiddenError):
    def __init__(self, backend_name, repository_name):
        super(BackendRepositoryForbiddenError, self).__init__(
            '`%s` access if forbidden by %s' % (
                repository_name, backend_name)
        )

class BackendUnauthorizedError(BackendAccessError):
    def __init__(self, message=None):
        super(BackendUnauthorizedError, self).__init__(
            message or 'The wanted access is not authorized', 401)

class BackendAccountUnauthorizedError(BackendUnauthorizedError):
    def __init__(self, backend_name, account_name):
        super(BackendAccountUnauthorizedError, self).__init__(
            '`%s` access not authorized by %s' % (
                account_name, backend_name)
        )

class BackendRepositoryUnauthorizedError(BackendUnauthorizedError):
    def __init__(self, backend_name, repository_name):
        super(BackendRepositoryUnauthorizedError, self).__init__(
            '`%s` access if not authorized by %s' % (
                repository_name, backend_name)
        )

class BackendInternalError(BackendError):
    def __init__(self, message=None, code=None):
        super(BackendError, self).__init__(
            message or 'The bakend encountered an internal error, preventing us to accomplish your request',
            code)

