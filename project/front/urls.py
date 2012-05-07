# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from front.views import main, fetch

urlpatterns = patterns('',
    url(r'^fetch/$', fetch, name='fetch'),
    url(r'^$', main, name='front_main'),
)
