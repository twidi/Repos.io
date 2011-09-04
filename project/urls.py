from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {'template': 'home.html'}, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'accounts/', include('accounts.urls')),
    url(r'^(?P<slug>\w+)@(?P<backend>\w+)/', include('personal.urls')),
)
