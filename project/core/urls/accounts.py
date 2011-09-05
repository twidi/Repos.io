from django.conf.urls.defaults import *

from core.views.accounts import *

urlpatterns = patterns('',
    url(r'^$', home, name='account_home'),
    url(r'^followers/$', followers, name='account_followers'),
    url(r'^following/$', following, name='account_following'),
    url(r'^repositories/$', repositories, name='account_repositories'),
)

