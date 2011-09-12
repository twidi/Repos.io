from django.conf.urls.defaults import *

from user_notes.views import save

urlpatterns = patterns('',
    url(r'^save/', save, name='note_save'),
)
