from django.conf.urls.defaults import *

from private.views import note_save, note_delete, tags_save, tags_delete

urlpatterns = patterns('',
    url(r'^notes/save/', note_save, name='note_save'),
    url(r'^notes/delete/', note_delete, name='note_delete'),
    url(r'^tags/save/', tags_save, name='tags_save'),
    url(r'^tags/delete/', tags_delete, name='tags_delete'),
)
