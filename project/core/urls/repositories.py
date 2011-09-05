from django.conf.urls.defaults import *

from core.views.repositories import *

urlpatterns = patterns('',
    url(r'^$', home, name='repository_home'),
    url(r'^followers/$', followers, name='repository_followers'),
    url(r'^contributors/$', contributors, name='repository_contributors'),
)

