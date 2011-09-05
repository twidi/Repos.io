from core.backends import BACKENDS_BY_AUTH
from core.models import Account, Repository

def backends(request):
    return dict(
        backends_map = dict((backend.name, auth_backend) for auth_backend, backend in BACKENDS_BY_AUTH.items())
    )

def objects(request):
    return dict(
        accounts_manager = Account.objects,
        repositories_manager = Repository.objects,
    )
