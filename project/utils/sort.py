# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

# example of sort map :
#repository_sort_map = dict(
#    request_key = 'db_field'
#    name = 'slug_sort',
#    owner = 'owner__slug_sort',
#    updated = 'official_modified',
#)


def prepare_sort(key, sort_map, default, default_reverse):
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

