# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from django.shortcuts import HttpResponseRedirect

def redirect_dashboard(request, search_type, search_filter, options=None):
    if not options:
        options = {}
    q = request.REQUEST.get('q', '')
    order = request.REQUEST.get('sort_by', '')
    url = '/v2/?type=%s&q=%s&filter=%s%s&order=%s' % (
        search_type,
        q,
        search_filter,
        '&%s' % (''.join(['%s=%s' % (opt_key, opt_value) for opt_key, opt_value in options.items()]),),
        order
    )
    return HttpResponseRedirect(url)

def redirect_followers(request):
    return redirect_dashboard(request, 'people', 'followers')

def redirect_following(request):
    return redirect_dashboard(request, 'people', 'following')

def redirect_repositories(request):
    search_filter = 'following'
    if request.REQUEST.get('owner-only', 'n') == 'y':
        search_filter = 'owned'
    options = {}
    if request.REQUEST.get('hide-forks', 'n') == 'n':
        options['show_forks'] = 'y'
    return redirect_dashboard(request, 'repositories', search_filter, options)

def redirect_contributing(request):
    search_filter = 'contributed'
    if request.REQUEST.get('owner-only', 'n') == 'y':
        search_filter = 'owned'
    options = {}
    if request.REQUEST.get('hide-forks', 'n') == 'n':
        options['show_forks'] = 'y'
    return redirect_dashboard(request, 'repositories', search_filter, options)

def redirect_notes(request, obj_type):
    search_type = 'repositories'
    if obj_type == 'accounts':
        search_type = 'people'
    return redirect_dashboard(request, search_type, 'noted')

def redirect_tags(request, obj_type):
    options = {}
    search_type = 'repositories'
    if obj_type == 'accounts':
        search_type = 'people'
    else:
        options['show_forks'] = 'y'
    search_filter = 'tagged'
    tag = request.REQUEST.get('tag', '')
    if tag:
        search_filter = 'tag:%s' % tag
    return redirect_dashboard(request, search_type, search_filter, options)


urlpatterns = patterns('',
    url(r'^$', redirect_repositories, name='dashboard_home'),
    url(r'^tags(?:/(?P<obj_type>repositories|accounts))?/$', redirect_tags, name='dashboard_tags'),
    url(r'^notes(?:/(?P<obj_type>repositories|accounts))?/$', redirect_notes, name='dashboard_notes'),
    url(r'^following/$', redirect_following, name='dashboard_following'),
    url(r'^followers/$', redirect_following, name='dashboard_followers'),
    url(r'^repositories/$', redirect_repositories, name='dashboard_repositories'),
    url(r'^contributing/$', redirect_contributing, name='dashboard_contributing'),
)
