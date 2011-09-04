from django.conf.urls.defaults import *
from personal.views import watching

urlpatterns = patterns('',
    url('watching/', watching, name='personal_watching'),
)
