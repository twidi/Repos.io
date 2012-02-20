# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *

from core.views.accounts import *

urlpatterns = patterns('',
    url(r'^$', home, name='account_home'),
    url(r'^edit-tags/$', edit_tags, name='account_edit_tags'),
    url(r'^edit-note/$', edit_note, name='account_edit_note'),
    url(r'^about/$', about, name='account_about'),

    url(r'^followers/$', followers, name='account_followers'),
    url(r'^following/$', following, name='account_following'),
    url(r'^repositories/$', repositories, name='account_repositories'),
    url(r'^contributing/$', contributing, name='account_contributing'),
)

