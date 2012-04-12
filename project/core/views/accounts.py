# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render, redirect

from endless_pagination.decorators import page_template

from core.views.decorators import check_account, check_support
from core.views import base_object_search
from front.decorators import ajaxable
from private.forms import NoteForm
from utils.views import ajax_login_required

@check_account
@ajaxable('front/account_details.html')
def home(request, backend, slug, account=None, template='front/account_main.html'):
    """
    Home page of an account
    """
    context = dict(obj = account)
    return render(request, template, context)

@check_account
@ajaxable('front/account_details.html')
def edit_tags(request, backend, slug, account=None, template='front/account_main.html'):
    """
    Home page of an account, in tags-editing mode
    """
    context = dict(obj = account)
    if not request.is_ajax():
        context['edit_tags'] = True
    return render(request, template, context)

@check_account
@ajax_login_required
#@ajaxable('front/account_details.html')
@ajaxable('front/note_form.html')
def edit_note(request, backend, slug, account=None, template='front/account_main.html'):
    """
    Home page of an account, in tags-editing mode
    """
    note = account.get_user_note()

    context = dict(
        overlay = True,
        obj = account,
        edit_note = True,
        note = note,
        note_form = NoteForm(instance=note) if note else NoteForm(noted_object=account),
    )
    return render(request, template, context)

@check_support('user_followers')
@check_account
@page_template("front/include_results.html")
def followers(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing accounts following an account
    """
    return base_object_search(
            request,
            account,
            'people',
            'followers',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('user_following')
@check_account
@page_template("front/include_results.html")
def following(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing accounts followed by an account
    """
    return base_object_search(
            request,
            account,
            'people',
            'following',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('user_repositories')
@check_account
@page_template("front/include_results.html")
def repositories(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing repositories owned/watched by an account
    """
    return base_object_search(
            request,
            account,
            'repositories',
            'repositories',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('repository_contributors')
@check_account
@page_template("front/include_results.html")
def contributing(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing repositories with contributions by an account
    """
    return base_object_search(
            request,
            account,
            'repositories',
            'contributing',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_account
def about(request, backend, slug, account=None):

    if not request.is_ajax():
        return redirect(account)

    context = dict(obj = account)
    return render(request, 'front/include_subsection_about.html', context)

#def _filter_repositories(request, account, queryset):
#    """
#    Helper doing all sort/query stuff about repositories, for listing
#    repositories owned/followed or contributed by an account,
#    """
#    sort_key = request.GET.get('sort_by', 'name')
#    repository_supports_owner = account.get_backend().supports('repository_owner')
#    repository_supports_parent_fork = account.get_backend().supports('repository_parent_fork')
#    sort = get_repository_sort(sort_key, repository_supports_owner)
#
#    sorted_repositories = queryset.order_by(sort['db_sort'])
#
#    if repository_supports_owner:
#        owner_only = request.GET.get('owner-only', False) == 'y'
#    else:
#        owner_only = False
#
#    if owner_only:
#        sorted_repositories = sorted_repositories.filter(owner=account)
#
#    if repository_supports_parent_fork:
#        hide_forks = request.GET.get('hide-forks', False) == 'y'
#    else:
#        hide_forks = False
#
#    if hide_forks:
#        sorted_repositories = sorted_repositories.exclude(is_fork=True)
#
#    query = request.GET.get('q')
#    if query:
#        keywords = parse_keywords(query)
#        search_queryset = make_query(RepositorySearchView.search_fields, keywords)
#        search_queryset = search_queryset.models(RepositorySearchView.model)
#        if owner_only:
#            search_queryset = search_queryset.filter(owner_id=account.id)
#        if hide_forks:
#            search_queryset = search_queryset.exclude(is_fork=True)
#        # It's certainly not the best way to do it but.... :(
#        sorted_ids = [r.id for r in sorted_repositories]
#        if sorted_ids:
#            search_queryset = search_queryset.filter(django_id__in=sorted_ids)
#            found_ids = [int(r.pk) for r in search_queryset]
#            sorted_repositories = [r for r in sorted_repositories if r.id in found_ids]
#
#    distinct = request.GET.get('distinct', False) == 'y'
#    if distinct and not owner_only:
#        # try to keep one entry for each slug
#        uniq = []
#        slugs = {}
#        for repository in sorted_repositories:
#            if repository.slug in slugs:
#                slugs[repository.slug].append(repository)
#                continue
#            slugs[repository.slug] = []
#            uniq.append(repository)
#        for repository in uniq:
#            repository.distinct_others = slugs[repository.slug]
#        # try to keep the first non-fork for each one
#        sorted_repositories = []
#        sort_lambda = lambda r:r.official_created
#        for repository in uniq:
#            if not repository.distinct_others or repository.owner_id == account.id:
#                good_repository = repository
#            else:
#                important_ones = [r for r in repository.distinct_others if not r.is_fork]
#                owned = [r for r in important_ones if r.owner_id == account.id]
#                if owned:
#                    good_repository = owned[0]  # only one possible
#                else:
#                    if important_ones:
#                        if not repository.is_fork:
#                            important_ones + [repository,]
#                    else:
#                        important_ones = repository.distinct_others + [repository,]
#
#                    good_repository = sorted(important_ones, key=sort_lambda)[0]
#
#                if good_repository != repository:
#                    good_repository.distinct_others = [r for r in repository.distinct_others + [repository,] if r != good_repository]
#                    delattr(repository, 'distinct_others')
#
#                if hasattr(good_repository, 'distinct_others'):
#                    good_repository.distinct_others = sorted(good_repository.distinct_others, key=sort_lambda)
#
#            sorted_repositories.append(good_repository)
#
#    page = paginate(request, sorted_repositories, settings.REPOSITORIES_PER_PAGE)
#
#    return dict(
#        account = account,
#        page = page,
#        sort = dict(
#            key = sort['key'],
#            reverse = sort['reverse'],
#        ),
#        owner_only = 'y' if owner_only else False,
#        hide_forks = 'y' if hide_forks else False,
#        distinct = 'y' if distinct else False,
#        query = query or "",
#    )

