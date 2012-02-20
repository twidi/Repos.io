# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render, redirect
from django.http import Http404

from endless_pagination.decorators import page_template

from core.views.decorators import check_repository, check_support
from core.views import base_object_search
from front.decorators import ajaxable
from private.forms import NoteForm

@check_repository
@ajaxable('front/repository_details.html')
def home(request, backend, project, repository=None, template='front/repository_main.html'):
    """
    Home page of a repository
    """
    context = dict(obj = repository)
    return render(request, template, context)

@check_repository
@ajaxable('front/repository_details.html')
def edit_tags(request, backend, project, repository=None, template='front/repository_main.html'):
    """
    Home page of a repository, in tags-editing mode
    """
    context = dict(obj = repository)
    if not request.is_ajax():
        context['edit_tags'] = True
    return render(request, template, context)

@check_repository
#@ajaxable('front/repository_details.html')
@ajaxable('front/note_form.html')
def edit_note(request, backend, project, repository=None, template='front/repository_main.html'):
    """
    Home page of a repository, in tags-editing mode
    """
    note = repository.get_user_note()

    context = dict(
        overlay = True,
        obj = repository,
        edit_note = True,
        note = note,
        note_form = NoteForm(instance=note) if note else NoteForm(noted_object=repository),
    )
    return render(request, template, context)

@check_repository
def owner(request, backend, project, repository=None):
    """
    Link to the repository's owner page
    """
    if not repository.owner:
        raise Http404
    if not request.is_ajax():
        return redirect(repository.owner)

    repository.owner.include_details = 'about'

    context = dict(obj = repository.owner)

    return render(request, 'front/include_subsection_object.html', context)

@check_repository
def parent_fork(request, backend, project, repository=None):
    """
    Link to the repository's parent-fork page
    """
    if not repository.parent_fork:
        raise Http404
    if not request.is_ajax():
        return redirect(repository.parent_fork)

    repository.parent_fork.include_details = 'about'

    context = dict(obj = repository.parent_fork)

    return render(request, 'front/include_subsection_object.html', context)

@check_support('repository_followers')
@check_repository
@page_template("front/include_results.html")
def followers(request, backend, project, repository=None, template="front/repository_main.html", extra_context=None):
    """
    Page listing users following a repository
    """
    return base_object_search(
            request,
            repository,
            'people',
            'followers',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('repository_contributors')
@check_repository
@page_template("front/include_results.html")
def contributors(request, backend, project, repository=None, template="front/repository_main.html", extra_context=None):
    """
    Page listing users contributing to a repository
    """
    return base_object_search(
            request,
            repository,
            'people',
            'contributors',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('repository_readme')
@check_repository
@ajaxable('front/include_subsection_readme.html')
def readme(request, backend, project, repository=None, template="front/repository_main.html"):
    context = dict(obj = repository)
    return render(request, template, context)

@check_repository
def about(request, backend, project, repository=None):

    if not request.is_ajax():
        return redirect(repository)

    context = dict(obj = repository)
    return render(request, 'front/include_subsection_about.html', context)

@check_support('repository_parent_fork')
@check_repository
@page_template("front/include_results.html")
def forks(request, backend, project, repository=None, template="front/repository_main.html", extra_context=None):
    """
    Page listing forks of a repository
    """
    return base_object_search(
            request,
            repository,
            'repositories',
            'forks',
            template = template,
            search_extra_params = { 'show_forks': 'y' },
            extra_context = extra_context,
        )

    #if mode == 'real_forks':
    #    sorted_forks = Repository.for_list.filter(parent_fork=repository)
    #else:
    #    sorted_forks = Repository.for_list.filter(name=repository.name).exclude(is_fork=True)
    ## check sub forks, one query / level
    #if mode == 'real_forks':
    #    current_forks = page.object_list
    #    while True:
    #        by_id = dict((obj.id, obj) for obj in current_forks)
    #        current_forks = Repository.for_list.filter(parent_fork__in=by_id.keys()).order_by('-official_modified')
    #        if not current_forks:
    #            break
    #        for fork in current_forks:
    #            parent_fork = by_id[fork.parent_fork_id]
    #            if not hasattr(parent_fork, 'direct_forks'):
    #                parent_fork.direct_forks = []
    #            parent_fork.direct_forks.append(fork)
    #    # make one list for each first level fork, to avoid recursion in templates
    #    all_forks = []
    #    def get_all_forks_for(fork, level):
    #        fork.fork_level = level
    #        all_subforks = [fork,]
    #        if hasattr(fork, 'direct_forks'):
    #            for subfork in fork.direct_forks:
    #                all_subforks += get_all_forks_for(subfork, level+1)
    #            delattr(fork, 'direct_forks')
    #        return all_subforks
    #    for fork in page.object_list:
    #        all_forks += get_all_forks_for(fork, 0)
    #    page.object_list = all_forks



