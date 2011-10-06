from django.conf.urls.defaults import *
from dashboard.views import home, tags, notes, following, followers, repositories, contributing

urlpatterns = patterns('',
    url(r'^$', home, name='dashboard_home'),
    url(r'^tags(?:/(?P<obj_type>repositories|accounts))?/$', tags, name='dashboard_tags'),
    url(r'^notes/$', notes, name='dashboard_notes'),
    url(r'^following/$', following, name='dashboard_following'),
    url(r'^followers/$', followers, name='dashboard_followers'),
    url(r'^repositories/$', repositories, name='dashboard_repositories'),
    url(r'^contributing/$', contributing, name='dashboard_contributing'),
)

