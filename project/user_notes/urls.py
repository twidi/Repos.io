from django.conf.urls.defaults import *

from user_notes.views import save, delete

urlpatterns = patterns('',
    url(r'^save/', save, name='note_save'),
    url(r'^delete/', delete, name='note_delete'),
)
