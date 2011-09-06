
def design(request):
    """
    Some tools for design
    """

    # calculate the current section
    if request.path == '/':
        section = 'home'
    elif request.path.startswith('/accounts/'):
        section = 'accounts'
    elif request.path.startswith('/user/'):
        section = 'user'
    elif request.path.startswith('/repository/'):
        section = 'repository'
    else:
        section = None

    # final result
    return dict(
        section  = section
    )
