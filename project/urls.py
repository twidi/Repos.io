from django.conf.urls.defaults import patterns, include, url

from views import home

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', home, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^search/', include('search.urls')),
    url(r'^private/', include('private.urls')),
    url(r'^tags/', include('tagging.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^', include('core.urls')),
)
