from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from personal.decorators import check_account

_sort_map = dict(
    name = ('name', 'project name'),
    owner = ('official_owner', 'owner'),
    updated = ('official_modified', 'update date'),
)

@login_required
@check_account
def watching(request, slug, backend, account=None):

    # manage sort order
    sort = request.GET.get('sort_by', 'name')
    if sort[0] == '-':
        sort = sort[1:]
        reverse = True
    else:
        reverse = False
    if sort not in ('name', 'owner', 'updated'):
        sort = 'name'
        reverse = False

    real_sort = _sort_map[sort][0]
    if reverse:
        real_sort = '-' + real_sort

    sorted_repositories = account.repositories.order_by(real_sort)

    return render(request, 'personal/watching.html', dict(
        account = account,
        sorted_repositories = sorted_repositories,
        sort = dict(
            key = sort,
            reverse = reverse,
            name = _sort_map[sort][1],
            others = dict((key, value[1]) for key, value in _sort_map.items() if key != sort),
        ),
    ))

