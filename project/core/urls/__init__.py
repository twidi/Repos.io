from django.conf.urls.defaults import *

from core.views import default

# urls with allowed backends only
from core.backends import BACKENDS
backend_part = r'(?P<backend>(?:%s))/' % '|'.join(BACKENDS.keys())

urlpatterns = patterns('',
    url(r'project/' + backend_part + '(?P<project>[\w\-\/]+)/', include('core.urls.repositories')),
    url(r'user/' + backend_part + '(?P<slug>\w+)/', include('core.urls.users')),
    url(r'(?P<identifier>[\w\/\-]+)', default, name='default'),
)
