from django.core.urlresolvers import resolve
from django.conf import settings

def caching(request):
    """
    Returns timeout to use in template caching
    """
    min_timeout = 1000000
    if settings.DEBUG:
        min_timeout = getattr(settings, 'DEBUG_MAX_TMPL_CACHE_TIMEOUT', None) or min_timeout
    return dict(cache_timeout=dict(
        repository_main_cell = min(86400, min_timeout),
        account_main_cell = min(86400, min_timeout),
        repository_owner_cell = min(86400, min_timeout),
        home_accounts = min(52, min_timeout),
        home_repositories = min(56, min_timeout),
        private_common_part = min(120, min_timeout),
        private_specific_part = min(300, min_timeout),
    ))

def design(request):
    """
    Some tools for design
    """

    section = None
    subsection = None

    # calculate the current section
    if request.path == '/':
        section = 'home'

    elif request.path.startswith('/search/'):
        section = 'search'
        if request.path.startswith('/search/users/'):
            subsection = 'accounts'
        else:
            subsection = 'repositories'

    elif request.path.startswith('/accounts/'):
        section = 'accounts'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "accounts_" part
            subsection = url_name[9:]

    elif request.path.startswith('/user/'):
        section = 'user'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "account_" part
            subsection = url_name[8:]

    elif request.path.startswith('/project/'):
        section = 'repository'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "repository_" part
            subsection = url_name[11:]

    elif request.path.startswith('/dashboard/'):
        section = 'dashboard'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "dashboard_" part
            subsection = url_name[10:]

    # final result
    return dict(
        section  = section,
        subsection = subsection,
        current_request = request.get_full_path(),
    )
