from core.backends import BACKENDS_BY_AUTH

def backends(request):
    return dict(
        backends_map = dict((backend.name, auth_backend) for auth_backend, backend in BACKENDS_BY_AUTH.items())
    )
