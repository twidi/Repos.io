from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from personal.decorators import check_account
from github2.client import Github
from django.core.cache import cache

@login_required
@check_account
def watching(request, login, provider, social_user=None):


    cache_key = '%s:%s:watching' % (provider, login)
    repositories = cache.get(cache_key)
    if repositories is None:
        github = Github(
            access_token=social_user.extra_data.get('access_token'),
            #request_per_second=1
        )

        repositories = github.repos.watching(for_user=login)
        cache.set(cache_key, repositories, 60*5)

    return render(request, 'personal/watching.html', dict(
        login = login,
        provider = provider,
        social_user = social_user,
        repositories = repositories
    ))

