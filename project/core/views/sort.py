from copy import copy
from utils.sort import prepare_sort

repository_sort_map = dict(
    name = 'slug_sort',
    owner = 'owner__slug_sort',
    updated = 'official_modified',
)
account_sort_map = dict(
    name = 'slug_sort',
)

def get_repository_sort(key, allow_owner=True, default='name', default_reverse=False, disabled=None):
    """
    Return needed informations about sorting repositories
    """
    _repository_sort_map = copy(repository_sort_map)

    if not allow_owner:
        del _repository_sort_map['owner']

    if disabled:
        for entry in disabled:
            _repository_sort_map.pop(entry, None)

    return prepare_sort(key, _repository_sort_map, default, default_reverse)

def get_account_sort(key, default='name', default_reverse=False, disabled=None):
    """
    Return needed informations about sorting accounts
    """
    _account_sort_map = account_sort_map

    if disabled:
        _account_sort_map = copy(account_sort_map)
        for entry in disabled:
            _account_sort_map.pop(entry, None)

    return prepare_sort(key, _account_sort_map, default, default_reverse)
