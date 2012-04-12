from django.views.generic.simple import direct_to_template

def login(request):
    if request.REQUEST.get('iframe', False):
        template = 'accounts/login_iframe.html'
    else:
        template = 'accounts/login.html'
    return direct_to_template(request, template)
