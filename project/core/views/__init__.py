from django.shortcuts import render, redirect
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from core.backends import BACKENDS
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
        Q(project_sort=project_identifier) | Q(slug_sort=project_identifier))
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

@require_POST
@login_required
def fetch(request):
    """
    Try to fetch an object or its related objects
    """
    try:
        otype = request.POST['type']
        if otype not in ('account', 'repository'):
            raise
        id = int(request.POST['id'])
        backend = request.POST['backend']
        if backend not in BACKENDS:
            raise
        if otype == 'account':
            slug = request.POST['slug']
            obj = Account.objects.get(id=id, backend=backend, slug=slug)
        else:
            project = request.POST['project']
            obj = Repository.objects.get(id=id, backend=backend, project=project)
    except:
        return HttpResponseNotAllowed('Vilain :)')
    else:
        related = 'related' in request.POST

        if related:
            if obj.fetch_related_allowed():
                obj.fetch_related()
                messages.success(request, 'Fetch of related is successfull !')
            else:
                messages.error(request, 'Fetch of related is not allowed (maybe the last one is too recent')

        else:
            if obj.fetch_allowed():
                obj.fetch()
                messages.success(request, 'Fetch of this %s is successfull !' % otype)
            else:
                messages.error(request, 'Fetch is not allowed (maybe the last one is too recent')

    redirect_url = request.POST.get('next', '/')
    if not redirect_url.startswith('/'):
        redirect_url = '/'

    return redirect(redirect_url)

