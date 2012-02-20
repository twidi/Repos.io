# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *

from core.views.repositories import *

urlpatterns = patterns('',
    url(r'^$', home, name='repository_home'),
    url(r'^edit-tags/$', edit_tags, name='repository_edit_tags'),
    url(r'^edit-note/$', edit_note, name='repository_edit_note'),
    url(r'^about/$', about, name='repository_about'),

    url(r'^followers/$', followers, name='repository_followers'),
    url(r'^contributors/$', contributors, name='repository_contributors'),
    url(r'^forks/$', forks, name='repository_forks'),
    url(r'^readme/$', readme, name='repository_readme'),
    url(r'^owner/$', owner, name='repository_owner'),
    url(r'^parent-fork/$', parent_fork, name='repository_parent_fork'),
)

