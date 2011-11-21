# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from tagging.views import autocomplete

urlpatterns = patterns('',
    url(r'^autocomplete$', autocomplete, name='tagging_autocomplete'),
)

