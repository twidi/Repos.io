# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render

from endless_pagination.decorators import page_template

from private.views import get_user_tags
from front.search import Search

@page_template("front/include_results.html")
def main(request, template='front/main.html', extra_context=None):

    search = Search.get_for_params(request.REQUEST, request.user)

    tags = get_user_tags(request)

    context = dict(
        search = search,
        tags = tags
    )

    if extra_context is not None:
        context.update(extra_context)

    return render(request, template, context)
