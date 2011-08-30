class CoreException(Exception):
    pass

class SaveForbiddenInBackend(CoreException):
    def __init__(self, message):
        super(SaveForbiddenInBackend, self).__init__(message or 'You cannot save this object in the backend')

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
    def __init__(self, user, backend, message=None):
        super(SaveForbiddenInBackend, self).__init__(
            message or 'The original_login from the %s backend for the user %s is required' %
            (
                backend,
                user
            )
        )
