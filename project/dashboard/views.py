from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

def _get_sorted_user_tags(user):
    """
    Return all tags for the user, sorted by usage (desc) and name (asc)
    The result is a dict with two entries : `repository` and `account`,
    grouping tags for each categoties. Each list is a list of tuple, with
    the tag in first, and the list of tagged objects
    """
    result = {}
    types = dict(account='slug', repository='project')
    for type_related in types:
        tagged_items = getattr(user, 'tagging_privatetagged%s_items' % type_related).values_list('tag__slug', 'tag__name', 'content_object__%s' % types[type_related])
        tags = {}
        for tag_slug, tag_name, obj in tagged_items:
            if tag_slug not in tags:
                tags[tag_slug] = [tag_name, []]
            tags[tag_slug][1].append(obj)
        result[type_related] = [t[1] for t in sorted(tags.iteritems(), key=lambda t: (-len(t[1][1]), t[0]), reverse=False)]
    return result


@login_required
def home(request):
    """
    Home of the user dashboard.
    """

    def get_tags():
        return _get_sorted_user_tags(request.user)

    context = dict(
        tags = get_tags,
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
