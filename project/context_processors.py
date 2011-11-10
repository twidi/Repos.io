from django.core.urlresolvers import resolve

def caching(request):
    """
    Returns timeout to use in template caching
    """
    return dict(cache_timeout=dict(
        repository_main_cell = 86400,
        account_main_cell = 86400,
        repository_owner_cell = 86400,
        repository_extra = 300,
        account_extra = 300,
        home_accounts = 52,
        home_repositories = 56,
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
