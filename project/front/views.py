# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render

from core.models import Account, Repository

from tagging.models import Tag
from tagging.flags import split_tags_and_flags

def _get_tags(request):
    """
    Return the tags to be used in the search form filter.
    Work is done to note if tags are only for repositories, only for people
    or both.
    """
    # TODO => cache !
    tags = {}
    if request.user.is_authenticated():
        types = ('places', 'projects', 'tags')
        for model in ('account', 'repository'):
            tags[model] = split_tags_and_flags(Tag.objects.filter(
                **{'private_%s_tags__owner' % model: request.user}).distinct(), model)
            for todel in ('normal', 'special', 'special_used'):
                del tags[model][todel]
            for type_tag in types:
                tags[model][type_tag] = set(tags[model][type_tag])

        ta, tr = tags['account'], tags['repository']
        for type_tag in types:
            set_a, set_r = ta[type_tag], tr[type_tag]
            if not set_a and not set_r:
                tags['no_%s' % type_tag] = True
            elif not set_a:
                tags['%s_for_only' % type_tag] = 'repositories'
            elif not set_r:
                tags['%s_for_only' % type_tag] = 'people'
            else:
                for tag in set_r - set_a:
                    tag.for_only = 'repositories'
                for tag in set_a - set_r:
                    tag.for_only = 'people'
            tags[type_tag] = set_a.union(set_r)

        for type_tag in ('check-later', 'starred'):
            is_a, is_r = ta.get(type_tag, False), tr.get(type_tag, False)
            if not is_a and not is_r:
                tags['no_%s' % type_tag] = True
            elif not is_a:
                tags['%s_for_only' % type_tag] = 'repositories'
            elif not is_r:
                tags['%s_for_only' % type_tag] = 'people'

        del tags['account']
        del tags['repository']

    return tags

def test(request):
    import random

    model=Repository
    #model = random.choice((Account, Repository))
    #objects = list(model.for_list.order_by('id')[100:120])
    objects = list(model.for_list.filter(slug='django-critic').order_by('-score'))
    #random.shuffle(objects)

    with_details = []
    #if model == Repository:
    #    with_details = [objects[2].simple_str(), ]


    return render(request, 'front/test.html', dict(
        objects = objects,
        search_type = 'repository' if model == Repository else 'account',
        with_details = with_details,
        tags = _get_tags(request),
    ))
