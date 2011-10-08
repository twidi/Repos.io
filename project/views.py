from django.shortcuts import render

from core.models import Account, Repository

def home(request):
    context = dict(
        last_accounts = Account.for_list.filter(last_fetch__isnull=False).order_by('-last_fetch')[:20],
        last_repositories = Repository.for_list.filter(last_fetch__isnull=False).order_by('-last_fetch')[:20]
    )

    return render(request, 'home.html', context)
