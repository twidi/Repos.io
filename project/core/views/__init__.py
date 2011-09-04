from django.shortcuts import render, redirect
from django.db.models import Q

from core.utils import slugify
from core.models import Account, Repository

def default(request, identifier):
    """
    Try to find accounts or repositories matching the given identified
    """
    identifier = identifier.strip('/')

    # find matching accounts
    account_identifier = slugify(identifier)
    accounts = Account.objects.filter(slug_sort=account_identifier)
    accounts_count = accounts.count()

    # find matching repositories
    project_identifier = Repository.objects.slugify_project(identifier)
    repositories = Repository.objects.filter(
        Q(project_sort=project_identifier) | Q(name_sort=project_identifier))
    repositories_count = repositories.count()

    # only one result => redirect to its page
    if accounts_count + repositories_count == 1:
        if accounts_count:
            instance = accounts[0]
        else:
            instance = repositories[0]

        return redirect(instance)

    # else display all results
    return render(request, 'core/default.html', dict(
        identifier = identifier,
        count = dict(
            accounts = accounts_count,
            repositories = repositories_count,
            total = accounts_count + repositories_count,
        ),
        accounts = accounts,
        repositories = repositories,
    ))



