# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render

from core.models import Account, Repository

def home(request):
    mode = request.GET.get('show')
    if not mode or mode not in ('last', 'popular'):
        mode = 'last'

    context = dict(
        mode = mode
    )

    if mode == 'last':
        context['accounts'] = Account.for_list.get_last_fetched()
        context['repositories'] = Repository.for_list.get_last_fetched()
    else:
        context['accounts'] = Account.for_list.get_best(20)
        context['repositories'] = Repository.for_list.get_best(20)

    return render(request, 'home.html', context)
