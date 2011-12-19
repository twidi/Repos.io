# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from front.views import test

urlpatterns = patterns('',
    url(r'^$', test, name='front_test'),
)
