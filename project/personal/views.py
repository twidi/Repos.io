from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from personal.decorators import check_account

@login_required
@check_account
def watching(request, slug, backend, account=None):
    return render(request, 'personal/watching.html', dict(
        account = account,
    ))

