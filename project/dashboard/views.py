from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect


@login_required
def home(request):
    context = {}
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
