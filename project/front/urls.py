# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from front.views import main

urlpatterns = patterns('',
    url(r'^$', main, name='front_main'),
)
