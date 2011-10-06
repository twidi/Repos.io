from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

from notes.models import Note

from core.models import Account, Repository
from core.views.sort import get_repository_sort

def _get_sorted_user_tags(user, only=None):
    """
    Return all tags for the user, sorted by usage (desc) and name (asc)
    The result is a dict with two entries : `repository` and `account`,
    grouping tags for each category. Each list is a list of tuple, with
    the tag in first, and the list of tagged objects (only names)
    """
    result = {}
    types = dict(account='slug', repository='project')

    for obj_type in types:
        if only and obj_type != only:
            continue

        tagged_items = getattr(user, 'tagging_privatetagged%s_items' % obj_type).values_list('tag__slug', 'tag__name', 'content_object__%s' % types[obj_type])

        tags = {}
        if not tagged_items:
            continue

        for tag_slug, tag_name, obj in tagged_items:
            if tag_slug not in tags:
                tags[tag_slug] = [tag_slug, tag_name, []]
            tags[tag_slug][2].append(obj)

        result[obj_type] = [t[1] for t in sorted(tags.iteritems(), key=lambda t: (-len(t[1][2]), t[0]), reverse=False)]

    return result

def _get_last_user_notes(user, limit=None, only=None):
    """
    Return `limit` last noted objects (or all if no limit), sorted by date (desc).
    The result is a dict with two entries: `repotiroy` and `account`,
    grouping notes for each category. Each list is a list of typle, with
    the object (repository or account) and the rendered note
    """
    result = {}
    types = dict(account=Account, repository=Repository)

    for obj_type in types:
        if only and obj_type != only:
            continue

        notes = Note.objects.filter(author=user, content_type__app_label='core', content_type__model=obj_type).order_by('-modified').values_list('object_id', 'rendered_content')
        if limit:
            notes = notes[:limit]

        notes_by_obj_id = dict(notes)

        if not notes_by_obj_id:
            continue

        objs = types[obj_type].objects.in_bulk(notes_by_obj_id.keys())

        result[obj_type] = [(objs[note[0]], note[1])  for note in notes if note[0] in objs]

    print result
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
        return _get_last_user_notes(request.user, 10)

    best = dict(
        accounts = dict(
            followers = Account.objects.filter(following__user=request.user).order_by('-score')[:5],
            following = Account.objects.filter(followers__user=request.user).order_by('-score')[:5],
        ),
        repositories = dict(
            followed = Repository.objects.filter(followers__user=request.user).exclude(owner__user=request.user).order_by('-score')[:5],
            owned = Repository.objects.filter(owner__user=request.user).order_by('-score')[:5],
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
        return redirect(tags, obj_type='repositories', permanent=True)

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
        sort = get_repository_sort(sort_key)
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
def notes(request):
    messages.warning(request, '"Notes" page not ready : work in progress')
    return redirect(home)


@login_required
def following(request):
    messages.warning(request, '"Following" page not ready : work in progress')
    return redirect(home)


@login_required
def followers(request):
    messages.warning(request, '"Followers" page not ready : work in progress')
    return redirect(home)


@login_required
def repositories(request):
    messages.warning(request, '"Repositories" page not ready : work in progress')
    return redirect(home)


@login_required
def contributing(request):
    messages.warning(request, '"Contributions" page not ready : work in progress')
    return redirect(home)
