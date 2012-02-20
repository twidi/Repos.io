# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *

from private.views import note_save, note_delete, tags_save, tags_delete, ajax_edit, ajax_close, toggle, tag_save

urlpatterns = patterns('',
    url(r'^notes/save/$', note_save, name='note_save'),
    url(r'^notes/delete/$', note_delete, name='note_delete'),
    url(r'^tags/save/$', tags_save, name='tags_save'),
    url(r'^tags/delete/$', tags_delete, name='tags_delete'),
    url(r'^edit-ajax/(?P<object_key>(?:core\.)?(?:account|repository):\d+)/$', ajax_edit, name='private_ajax_edit'),
    url(r'^close-ajax/(?P<object_key>(?:core\.)?(?:account|repository):\d+)/$', ajax_close, name='private_ajax_close'),
    url(r'^toggle/(?P<key>star|check-later)/$', toggle, name='private_toggle'),
    url(r'^tag/save/$', tag_save, name='tag_save'),
)
