# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout
from accounts.decorators import anonymous_required

urlpatterns = patterns('',
    url(r'^manage/', login_required(direct_to_template), {'template': 'accounts/manage.html'}, name='accounts_manage'),
    url(r'^login/$', anonymous_required(direct_to_template), { 'template': 'accounts/login.html'}, name='accounts_login'),
    url(r'^logout/', login_required(logout), { 'template_name': 'home.html'}, name='accounts_logout'),
    url(r'', include('social_auth.urls')),
)
