# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest

from endless_pagination.decorators import page_template

from core.backends import get_backend
from core.models import Account, Repository
from core import messages as offline_messages
from private.views import get_user_tags
from front.search import Search
from utils.djson.response import JSONResponse
from utils.views import ajax_login_required

@page_template("front/include_results.html")
def main(request, template='front/main.html', extra_context=None):

    search = Search.get_for_params(request.REQUEST, request.user)

    tags = get_user_tags(request)

    context = dict(
        search = search,
        tags = tags
    )

    if extra_context is not None:
        context.update(extra_context)

    return render(request, template, context)


@require_POST
@ajax_login_required
@login_required
def fetch(request):
    """
    Trigger an asyncrhronous fetch_full of an object
    """

    try:
        otype = request.POST['type']
        if otype not in ('account', 'repository'):
            raise

        id = int(request.POST['id'])

        backend = get_backend(request.POST['backend'] or None)
        if not backend:
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
        obj.fetch_full(async=True, async_priority=4, notify_user=request.user, allowed_interval=obj.MIN_FETCH_DELTA)

        message = 'Fetch of %s is in the queue and will be done soon' % obj.str_for_user(request.user)

        if request.is_ajax():
            result = dict(
                message = message
            )

            return JSONResponse(result)

        offline_messages.success(request.user, message, content_object=obj)

        return redirect(obj)
