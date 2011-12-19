# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render

from core.models import Account, Repository

def test(request):
    import random
    l = 10
    objects = list(Repository.for_list.order_by('id')[100:100+l]) + list(Account.for_list.order_by('id')[100:100+l])

    with_details = [objects[2].simple_str(), ]

    random.shuffle(objects)

    return render(request, 'front/test.html', dict(
        objects = objects,
        with_details = with_details,
    ))
