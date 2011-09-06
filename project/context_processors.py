from django.core.urlresolvers import resolve

def design(request):
    """
    Some tools for design
    """

    section = None
    subsection = None

    # calculate the current section
    if request.path == '/':
        section = 'home'

    elif request.path.startswith('/accounts/'):
        section = 'accounts'

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

    # final result
    return dict(
        section  = section,
        subsection = subsection,
    )
