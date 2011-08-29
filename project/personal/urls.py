from django.conf.urls.defaults import *
from personal.views import watching

# place app url patterns here

urlpatterns = patterns('',
    url('watching/', watching, name='personal_watching'),
)
