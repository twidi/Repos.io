from django.http import Http404
from pure_pagination import Paginator, InvalidPage

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

def get_next(request):
    """
    Try to retrieve and return the "next" parameter. If not found, try with the
    referer and then the current path
    """
    return request.GET.get('next',
            request.META.get('HTTP_REFERER',
                None)
        ) or request.path
