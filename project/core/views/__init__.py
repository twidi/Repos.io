from django.shortcuts import render, redirect
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from core.backends import get_backend
from core.utils import slugify
from core.models import Account, Repository
from core.exceptions import BackendError, MultipleBackendError

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
        related = 'related' in request.POST

        otype = request.POST['type']
        if otype not in ('account', 'repository'):
            raise

        id = int(request.POST['id'])

        backend = get_backend(request.POST['backend'] or None)
        if not backend:
            raise

        # check if you can manage related for this type for this backend
        if related and not backend.supports(
                '%s_related' % ('user' if otype == 'account' else otype)):
            raise

        if otype == 'account':
            slug = request.POST['slug']
            obj = Account.objects.get(id=id, backend=backend.name, slug=slug)
        else:
            project = request.POST['project']
            obj = Repository.objects.get(id=id, backend=backend.name, project=project)
    except:
        return HttpResponseNotAllowed('Vilain :)')
    else:

        # find a access token
        access_token = None
        accounts = request.user.accounts.filter(backend=backend.name, access_token__isnull=False)
        for account in accounts:
            if account.access_token:
                access_token = account.access_token
                break

        if related:
            if obj.fetch_related_allowed():
                try:
                    obj.fetch_related(access_token=access_token)
                except MultipleBackendError, e:
                    for message in e.messages:
                        messages.error(request, message)
                except BackendError, e:
                    messages.error(request, e.message)
                else:
                    messages.success(request, 'Fetch of related is successfull !')
            else:
                messages.error(request, 'Fetch of related is not allowed (maybe the last one is too recent)')

        else:
            if obj.fetch_allowed():
                try:
                    obj.fetch(access_token=access_token)
                except BackendError, e:
                    messages.error(request, e.message)
                else:
                    messages.success(request, 'Fetch of this %s is successfull !' % otype)
            else:
                messages.error(request, 'Fetch is not allowed (maybe the last one is too recent)')

    redirect_url = request.POST.get('next', '/')
    if not redirect_url.startswith('/'):
        redirect_url = '/'

    return redirect(redirect_url)

