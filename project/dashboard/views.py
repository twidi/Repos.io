from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.conf import settings

from notes.models import Note

from core.models import Account, Repository
from core.views.sort import get_repository_sort,get_account_sort
from core.core_utils import get_user_accounts
from utils.sort import prepare_sort
from utils.views import paginate
from search.views import parse_keywords, make_query, RepositorySearchView

def _get_sorted_user_tags(user, only=None):
    """
    Return all tags for the user, sorted by usage (desc) and name (asc)
    The result is a dict with two entries : `repository` and `account`,
    grouping tags for each category. Each list is a list of tuple, with
    the tag's slug in first, then the tag's name and finally the list of
    tagged objects (only names)
    """
    result = {}
    types = dict(account='slug', repository='project')

    for obj_type in types:
        if only and obj_type != only:
            continue

        tagged_items = getattr(user, 'tagging_privatetagged%s_items' % obj_type).values_list('tag__slug', 'tag__name', 'content_object__%s' % types[obj_type])

        tags = {}
        if not tagged_items:
            result[obj_type] = []
            continue

        for tag_slug, tag_name, obj in tagged_items:
            if tag_slug not in tags:
                tags[tag_slug] = [tag_slug, tag_name, []]
            tags[tag_slug][2].append(obj)

        result[obj_type] = [t[1] for t in sorted(tags.iteritems(), key=lambda t: (-len(t[1][2]), t[0]), reverse=False)]

    return result

def _get_last_user_notes(user, limit=None, only=None, sort_by='-modified'):
    """
    Return `limit` last noted objects (or all if no limit), sorted by date (desc).
    The result is a dict with two entries: `repotiroy` and `account`,
    grouping notes for each category. Each list is a list of objects
    (repository or account) with a "current_user_rendered_note" added attribute
    """
    result = {}
    types = dict(account=Account, repository=Repository)

    for obj_type in types:
        if only and obj_type != only:
            continue

        result[obj_type] = []

        notes = Note.objects.filter(author=user, content_type__app_label='core', content_type__model=obj_type).values_list('object_id', 'rendered_content', 'modified')

        sort_objs = True
        if sort_by in ('-modified', 'modified'):
            sort_objs = False
            notes = notes.order_by(sort_by)

        if limit:
            notes = notes[:limit]

        if not notes:
            continue

        notes_by_obj_id = dict((note[0], note[1:]) for note in notes)

        if sort_objs:
            objs = types[obj_type].for_list.filter(id__in=notes_by_obj_id.keys()).order_by(sort_by)
            ordered = [obj for obj in objs if obj.id in notes_by_obj_id]
        else:
            objs = types[obj_type].for_list.in_bulk(notes_by_obj_id.keys())
            ordered = [objs[note[0]] for note in notes if note[0] in objs]

        for obj in ordered:
            obj.current_user_rendered_note, obj.current_user_note_modified = notes_by_obj_id[obj.id]
            obj.current_user_has_extra = obj.current_user_has_note = True
            result[obj_type].append(obj)

    return result


@login_required
def home(request):
    """
    Home of the user dashboard.
    For tags and notes we use callbacks, so they are only executed if
    called in templates
    For "best", it's simple querysets
    """

    def get_tags():
        return _get_sorted_user_tags(request.user)
    def get_notes():
        return _get_last_user_notes(request.user, 5)

    best = dict(
        accounts = dict(
            followers = Account.for_list.filter(following__user=request.user).order_by('-score').distinct()[:5],
            following = Account.for_list.filter(followers__user=request.user).order_by('-score').distinct()[:5],
        ),
        repositories = dict(
            followed = Repository.for_list.filter(followers__user=request.user).exclude(owner__user=request.user).order_by('-score').distinct()[:5],
            owned = Repository.for_list.filter(owner__user=request.user).order_by('-score').distinct()[:5],
        ),
    )

    context = dict(
        tags = get_tags,
        notes = get_notes,
        best = best,
    )
    return render(request, 'dashboard/home.html', context)

def obj_type_from_url(obj_type):
    """
    In url, we can have "accounts" and "repositories", but we need
    "account" and "repository".
    """
    if obj_type == 'accounts':
        return 'account'
    elif obj_type == 'repositories':
        return 'repository'
    else:
        return obj_type

@login_required
def tags(request, obj_type=None):
    """
    Display all tags for the given object type, and a list of tagged objects.
    A get parameter "tag" allow to filter the list.
    """
    if obj_type is None:
        return redirect(tags, obj_type='repositories')

    model = obj_type_from_url(obj_type)

    def get_tags():
        return _get_sorted_user_tags(request.user, only=model)[model]

    tag_slug = request.GET.get('tag', None)

    params = { 'privatetagged%s__owner' % model: request.user }
    if tag_slug:
        params['privatetagged%s__tag__slug' % model] = tag_slug

    sort_key = request.GET.get('sort_by', 'name')

    if model == 'account':
        objects = Account.objects.filter(**params)
        sort = get_account_sort(sort_key)
    else:
        objects = Repository.objects.filter(**params).select_related('owner')
        sort = get_repository_sort(sort_key)

    objects = objects.order_by(sort['db_sort'])

    context = dict(
        tags = get_tags,
        obj_type = obj_type,
        tag_filter = tag_slug,
        objects = objects,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )
    return render(request, 'dashboard/tags.html', context)


@login_required
def notes(request, obj_type=None):
    """
    Display all repositories or accounts with a note
    """
    if obj_type is None:
        return redirect(notes, obj_type='repositories')

    model = obj_type_from_url(obj_type)

    sort_key = request.GET.get('sort_by', '-note')
    if model == 'account':
        sort = get_account_sort(sort_key, default=None)
    else:
        sort = get_repository_sort(sort_key, default=None)
    if not sort.get('db_sort'):
        sort = prepare_sort(sort_key, dict(note='modified'), default='note', default_reverse=True)

    def get_notes():
        return _get_last_user_notes(request.user, only=model, sort_by=sort['db_sort'])[model]

    context = dict(
        noted_objects = get_notes,
        obj_type = obj_type,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )
    return render(request, 'dashboard/notes.html', context)


def accounts_dict(request):
    """
    Return a dict with all accounts of the current user
    """
    return dict((a.id, a) for a in get_user_accounts())


@login_required
def following(request):
    """
    Display following for all accounts of the user
    """

    all_following = Account.for_list.filter(followers__user=request.user).extra(select=dict(current_user_account_id='core_account_following.from_account_id'))

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    if sort['key']:
        all_following = all_following.order_by(sort['db_sort'])

    followers_ids = Account.objects.filter(following__user=request.user).values_list('id', flat=True)

    def get_accounts_dict():
        return accounts_dict(request)

    page = paginate(request, all_following, settings.ACCOUNTS_PER_PAGE)

    context = dict(
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        followers_ids = followers_ids,
        accounts = get_accounts_dict,
    )
    return render(request, 'dashboard/following.html', context)


@login_required
def followers(request):
    """
    Display followers for all accounts of the user
    """

    all_followers = Account.for_list.filter(following__user=request.user).extra(select=dict(current_user_account_id='core_account_following.to_account_id'))

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    if sort['key']:
        all_followers = all_followers.order_by(sort['db_sort'])

    following_ids = Account.objects.filter(followers__user=request.user).values_list('id', flat=True)

    def get_accounts_dict():
        return accounts_dict(request)

    page = paginate(request, all_followers, settings.ACCOUNTS_PER_PAGE)

    context = dict(
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        following_ids = following_ids,
        accounts = get_accounts_dict,
    )
    return render(request, 'dashboard/followers.html', context)


def _filter_repositories(request, param, extra):
    """
    Helper doing all sort/query stuff about repositories, for listing
    repositories owned/followed or contributed by the user
    """

    params = {param: request.user}

    owner_only = request.GET.get('owner-only', False) == 'y'
    if owner_only:
        params['owner__user'] = request.user

    all_repositories = Repository.for_list.filter(**params).extra(select=dict(current_user_account_id=extra))

    hide_forks = request.GET.get('hide-forks', False) == 'y'
    if hide_forks:
        all_repositories = all_repositories.exclude(is_fork=True)

    sort = get_repository_sort(request.GET.get('sort_by', None))
    if sort['key']:
        all_repositories = all_repositories.order_by(sort['db_sort'])

    accounts = accounts_dict(request)

    query = request.GET.get('q')
    if query:
        keywords = parse_keywords(query)
        search_queryset = make_query(RepositorySearchView.search_fields, keywords)
        search_queryset = search_queryset.models(RepositorySearchView.model)
        if owner_only:
            search_queryset = search_queryset.filter(owner_id__in=accounts.keys())
        if hide_forks:
            search_queryset = search_queryset.exclude(is_fork=True)
        # It's certainly not the best way to do it but.... :(
        sorted_ids = [r.id for r in all_repositories]
        if sorted_ids:
            search_queryset = search_queryset.filter(django_id__in=sorted_ids)
            found_ids = [int(r.pk) for r in search_queryset]
            all_repositories = [r for r in all_repositories if r.id in found_ids]

    distinct = request.GET.get('distinct', False) == 'y'
    if distinct:
        # try to keep one entry for each backend/slug
        uniq = []
        slugs = {}
        for repository in all_repositories:
            if repository.slug=='django-extended-choices':
                print repository
            slug = '%s:%s' % (repository.backend, repository.slug)
            if slug in slugs:
                slugs[slug].append(repository)
                continue
            slugs[slug] = []
            uniq.append(repository)
        for repository in uniq:
            slug = '%s:%s' % (repository.backend, repository.slug)
            repository.distinct_others = slugs[slug]
        # try to keep the first non-fork for each one
        all_repositories = []
        sort_lambda = lambda r:r.official_created
        for repository in uniq:
            if not repository.distinct_others or repository.owner_id in accounts:
                good_repository = repository
            else:
                important_ones = [r for r in repository.distinct_others if not r.is_fork]
                owned = [r for r in important_ones if r.owner_id in accounts]
                if owned:
                    good_repository = owned[0]  # all are from the owner, take one
                else:
                    if important_ones:
                        if not repository.is_fork:
                            important_ones + [repository,]
                    else:
                        important_ones = repository.distinct_others + [repository,]

                    good_repository = sorted(important_ones, key=sort_lambda)[0]

                if good_repository != repository:
                    good_repository.distinct_others = [r for r in repository.distinct_others + [repository,] if r != good_repository]
                    delattr(repository, 'distinct_others')

                if hasattr(good_repository, 'distinct_others'):
                    good_repository.distinct_others = sorted(good_repository.distinct_others, key=sort_lambda)

            good_repository.current_user_account_id_list = set((good_repository.current_user_account_id,))
            if hasattr(good_repository, 'distinct_others'):
                for other_rep in good_repository.distinct_others:
                    good_repository.current_user_account_id_list.add(other_rep.current_user_account_id)

            all_repositories.append(good_repository)

    page = paginate(request, all_repositories, settings.REPOSITORIES_PER_PAGE)

    context = dict(
        all_repositories = all_repositories,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        accounts = accounts,
        owner_only = 'y' if owner_only else False,
        hide_forks = 'y' if hide_forks else False,
        distinct = 'y' if distinct else False,
        query = query or "",
    )
    return context


@login_required
def repositories(request):
    """
    Display repositories followed/owned by the user
    """
    context = _filter_repositories(request, param='followers__user', extra='core_account_repositories.account_id')
    return render(request, 'dashboard/repositories.html', context)


@login_required
def contributing(request):
    """
    Display repositories contributed by the user
    """
    context = _filter_repositories(request, param='contributors__user', extra='core_repository_contributors.account_id')
    return render(request, 'dashboard/contributing.html', context)
