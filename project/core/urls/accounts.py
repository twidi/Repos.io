from django.conf.urls.defaults import *

from core.views.accounts import *

urlpatterns = patterns('',
    url(r'$', home, name='account_home'),
    url(r'followers/$', home, name='account_followers'),
    url(r'following/$', home, name='account_following'),
    url(r'repositories/$', home, name='account_repositories'),
)

