from django.conf.urls.defaults import *
from search.views import RepositorySearchView


urlpatterns = patterns('',
    url(r'^$', RepositorySearchView(), name='search'),
)
