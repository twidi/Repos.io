from copy import copy

_repository_sort_map = dict(
    name = 'slug_sort',
    owner = 'owner__slug_sort',
    updated = 'official_modified',
)
_account_sort_map = dict(
    name = 'slug_sort',
)


def _get_sort(key, sort_map, default, default_reverse):
    """
    Return needed informations about sorting (field to sort on in db, the key
    for the url, and if it's descending or ascending).
    The `key` must be in `sort_map`
    """
    reverse = False

    if key:
        if key[0] == '-':
            key = key[1:]
            reverse = True

        if key not in sort_map:
            key = default
            reverse = default_reverse

    if key:
        db_sort = sort_map[key]
        if reverse:
            db_sort = '-' + db_sort
    else:
        db_sort = None
        key = None

    return dict(
        db_sort = db_sort,
        key = key,
        reverse = reverse,
    )

def get_repository_sort(key, allow_owner=True, default='name', default_reverse=False):
    """
    Return needed informations about sorting repositories
    """
    repository_sort_map = copy(_repository_sort_map)

    if not allow_owner:
        del repository_sort_map['owner']

    return _get_sort(key, repository_sort_map, default, default_reverse)

def get_account_sort(key, default='name', default_reverse=False):
    """
    Return needed informations about sorting accounts
    """
    return _get_sort(key, _account_sort_map, default, default_reverse)
