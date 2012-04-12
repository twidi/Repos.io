# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', include('front.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^search/', include('search.urls')),
    url(r'^private/', include('private.urls')),
    url(r'^tags/', include('tagging.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^', include('core.urls')),
)
