# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.http import Http404
from pure_pagination import Paginator, InvalidPage
from utils.djson.response import JSONResponse

def paginate(request, objects, per_page):
    """
    Paginate the given `objects` list, with `per_page` entries per page,
    using the `page` GET parameter from the request
    """
    paginator = Paginator(objects, per_page, request=request)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404
    else:
        return page

def get_request_param(request, key='next', default=None):
    """
    Try to retrieve and return the `key` parameter.
    """
    return request.POST.get(key, request.GET.get(key, None)) or default

def _ajax_login_required(msg):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.is_ajax() and not request.user.is_authenticated():
                return JSONResponse({'login_required': True, 'error': msg})
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def ajax_login_required(function=None, msg='You need to be logged for this'):
    actual_decorator = _ajax_login_required(msg)
    if function:
        return actual_decorator(function)
    return actual_decorator
