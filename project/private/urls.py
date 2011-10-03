from django.conf.urls.defaults import *

from private.views import note_save, note_delete

urlpatterns = patterns('',
    url(r'^notes/save/', note_save, name='note_save'),
    url(r'^notes/delete/', note_delete, name='note_delete'),
)
