from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from core.backends import get_backend
from core.models import Account, Repository
from core.exceptions import BackendError, MultipleBackendError
from core.tokens import AccessTokenManager

def default(request, identifier):
    """
    Redirect to the search page
    """
    identifier = identifier.strip('/')

    search_url = reverse('search')

    return redirect(search_url + '?q='+identifier)


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
        token = AccessTokenManager.get_for_backend(obj.backend).get_one(wait=False)

        if not token:
            messages.error(request, 'Fetch is not possible right now, all the workers are working hard...')

        elif related:
            if obj.fetch_related_allowed():
                try:
                    obj.fetch_related(token=token)
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
                    obj.fetch(token=token)
                except BackendError, e:
                    messages.error(request, e.message)
                else:
                    messages.success(request, 'Fetch of this %s is successfull !' % otype)
            else:
                messages.error(request, 'Fetch is not allowed (maybe the last one is too recent)')

        if token:
            token.release()

    redirect_url = request.POST.get('next', '/')
    if not redirect_url.startswith('/'):
        redirect_url = '/'

    return redirect(redirect_url)
