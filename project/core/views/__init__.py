# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from core.backends import get_backend
from core.models import Account, Repository
from core.exceptions import BackendError, BackendSuspendedTokenError, MultipleBackendError
from core.tokens import AccessTokenManager
from front.search import Search
from front.decorators import ajaxable


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
        return HttpResponseBadRequest('Vilain :)')
    else:

        # find a access token
        token = AccessTokenManager.get_for_backend(obj.backend).get_one(wait=False)

        if not token:
            messages.error(request, 'Fetch is not possible right now, all the workers are working hard...')

        elif related:
            if obj.fetch_related_allowed():
                try:
                    obj.fetch_related(token=token)
                except BackendError, e:
                    messages.error(request, 'Fetch of related failed :(')

                    exceptions = [e]
                    if isinstance(e, MultipleBackendError):
                        exceptions = e.exceptions

                    for ex in exceptions:
                        if isinstance(ex, BackendSuspendedTokenError):
                            token.suspend(ex.extra.get('suspended_until'), str(ex))
                        elif isinstance(ex, BackendError) and ex.code:
                            if ex.code == 401:
                                token.set_status(ex.code, str(ex))
                            elif ex.code in (403, 404):
                                obj.set_backend_status(ex.code, str(ex))

                else:
                    messages.success(request, 'Fetch of related is successful!')
            else:
                messages.error(request, 'Fetch of related is not allowed (maybe the last one is too recent)')

        else:
            if obj.fetch_allowed():
                try:
                    obj.fetch(token=token)
                except BackendError, e:
                    messages.error(request, 'Fetch of this %s failed :(' % otype)

                    if isinstance(e, BackendSuspendedTokenError):
                        token.suspend(e.extra.get('suspended_until'), str(e))
                    elif isinstance(e, BackendError) and e.code:
                        if e.code == 401:
                            token.set_status(e.code, str(e))
                        elif e.code in (403, 404):
                            obj.set_backend_status(e.code, str(e))

                else:
                    messages.success(request, 'Fetch of this %s is successful!' % otype)
            else:
                messages.error(request, 'Fetch is not allowed (maybe the last one is too recent)')

        if token:
            token.release()

    redirect_url = request.POST.get('next', '/')
    if not redirect_url.startswith('/'):
        redirect_url = '/'

    return redirect(redirect_url)

@ajaxable("front/include_subsection.html", ignore_if=('page', ))
def base_object_search(request, obj, search_type, search_filter, template=None, search_extra_params=None, extra_context=None):
    """
    Base view used to search for objects of type `search_filter`, which are
    `search_type` (people or repositories) relatives to `obj`.
    """
    search_params = {
            'base': obj,
            'type': search_type,
            'filter': search_filter,
        }
    if search_extra_params:
        search_params.update(search_extra_params)

    search_params.update(Search.get_params_from_request(request, search_type, ignore=search_params))
    search = Search.get_for_params(search_params)

    context = {
            'search': search,
            'obj': obj,
        }

    if extra_context is not None:
        context.update(extra_context)

    return render(request, template, context)
