# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from django.shortcuts import HttpResponsePermanentRedirect

def redirect_search(request, search_type, options=None):
    if not options:
        options = ()
    q = request.REQUEST.get('q', '')
    order = request.REQUEST.get('sort_by', '')
    url = '/?type=%s&q=%s&filter=%s&order=%s' % (
        search_type,
        q,
        ''.join(['&%s=%s' % (opt_key.replace('-', '_'), request.REQUEST.get(opt_key)) for opt_key in options]),
        order
    )

    return HttpResponsePermanentRedirect(url)

def redirect_search_repositories(request):
    return redirect_search(request, 'repositories', ('show-forks',))

def redirect_search_accounts(request):
    return redirect_search(request, 'people')

urlpatterns = patterns('',
    url(r'^$', redirect_search_repositories, name='search'),
    url(r'^users/$', redirect_search_accounts, name='search_accounts'),
)
