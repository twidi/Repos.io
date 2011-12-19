# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render

from core.models import Account, Repository

def test(request):
    import random

    model = random.choice((Account, Repository))
    objects = list(model.for_list.order_by('id')[100:110])
    random.shuffle(objects)

    with_details = []
    if model == Repository:
        with_details = [objects[2].simple_str(), ]

    return render(request, 'front/test.html', dict(
        objects = objects,
        search_type = 'repository' if model == Repository else 'account',
        with_details = with_details,
    ))
