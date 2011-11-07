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
