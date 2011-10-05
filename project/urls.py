from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {'template': 'home.html'}, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^search/', include('search.urls')),
    url(r'^private/', include('private.urls')),
    url(r'^tags/', include('tagging.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^', include('core.urls')),
)
