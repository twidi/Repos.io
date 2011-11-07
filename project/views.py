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
        context['accounts'] = Account.for_list.filter(last_fetch__isnull=False).order_by('-last_fetch')[:20]
        context['repositories'] = Repository.for_list.filter(last_fetch__isnull=False).order_by('-last_fetch')[:20]
    else:
        context['accounts'] = Account.for_list.order_by('-score')[:20]
        context['repositories'] = Repository.for_list.order_by('-score')[:20]

    return render(request, 'home.html', context)
