from tagging.models import Tag
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError

def autocomplete(request):
    try:
        tags = Tag.objects.filter(name__istartswith=request.GET['q']).values_list('name', flat=True)
    except MultiValueDictKeyError:
        tags = []
    return HttpResponse('\n'.join(tags), mimetype='text/plain')
