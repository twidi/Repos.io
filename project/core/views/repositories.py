from django.shortcuts import render

from core.views.decorators import check_repository

@check_repository
def home(request, backend, project, repository=None):
    """
    Home page of a repository
    """
    return render(request, 'core/repositories/home.html', dict(
        repository = repository
    ))

@check_repository
def followers(request, backend, project, repository=None):
    """
    Page listing users following a repository
    """
    return render(request, 'core/repositories/followers.html', dict(
        repository = repository
    ))

