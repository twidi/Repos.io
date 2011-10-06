from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

from notes.models import Note

from core.models import Account, Repository

def _get_sorted_user_tags(user):
    """
    Return all tags for the user, sorted by usage (desc) and name (asc)
    The result is a dict with two entries : `repository` and `account`,
    grouping tags for each category. Each list is a list of tuple, with
    the tag in first, and the list of tagged objects (only names)
    """
    result = {}
    types = dict(account='slug', repository='project')

    for obj_type in types:

        tagged_items = getattr(user, 'tagging_privatetagged%s_items' % obj_type).values_list('tag__slug', 'tag__name', 'content_object__%s' % types[obj_type])

        tags = {}
        if not tagged_items:
            continue

        for tag_slug, tag_name, obj in tagged_items:
            if tag_slug not in tags:
                tags[tag_slug] = [tag_name, []]
            tags[tag_slug][1].append(obj)

        result[obj_type] = [t[1] for t in sorted(tags.iteritems(), key=lambda t: (-len(t[1][1]), t[0]), reverse=False)]

    return result

def _get_last_user_notes(user, limit=None):
    """
    Return `limit` last noted objects (or all if no limit), sorted by date (desc).
    The result is a dict with two entries: `repotiroy` and `account`,
    grouping notes for each category. Each list is a list of typle, with
    the object (repository or account) and the rendered note
    """
    result = {}
    types = dict(account=Account, repository=Repository)

    for obj_type in types:

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
    """

    def get_tags():
        return _get_sorted_user_tags(request.user)
    def get_notes():
        return _get_last_user_notes(request.user, 5)

    context = dict(
        tags = get_tags,
        notes = get_notes,
    )
    return render(request, 'dashboard/home.html', context)


@login_required
def tags(request):
    messages.warning(request, '"Tags" page not ready : work in progress')
    return redirect(home)


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
