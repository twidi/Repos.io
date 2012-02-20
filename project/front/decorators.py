# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from functools import wraps

def ajaxable(template, ignore_if=None):
    """
    If the request is an ajax one, then call the view with the template given
    as parameter to this decorator instead of the original one.
    The view MUST have the template in its parameters
    """
    def decorator(view):
        #decorator with arguments wrap
        @wraps(view)
        def decorated(request, *args, **kwargs):
            if request.is_ajax():
                ignore = False
                if ignore_if:
                    for field in ignore_if:
                        if field in request.REQUEST:
                            ignore = True
                            break
                if not ignore:
                    kwargs['template'] = template
            return view(request, *args, **kwargs)
        return decorated
    return decorator

