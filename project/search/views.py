from django.http import Http404

from pure_pagination import Paginator, InvalidPage
from saved_searches.views import SavedSearchView as BaseSearchView
from saved_searches.models import SavedSearch

from search.forms import RepositorySearchForm, AccountSearchForm

class PurePaginationSearchView(BaseSearchView):

    def build_page(self):
        """
        Use django-pure-pagination
        """
        paginator = Paginator(self.results, self.results_per_page, request=self.request)
        try:
            page = paginator.page(self.request.GET.get('page', 1))
        except InvalidPage:
            raise Http404

        return (paginator, page)


class RepositorySearchView(PurePaginationSearchView):
    """
    Class based view to handle search of repositories
    """
    __name__ = 'RepositorySearchView'
    template = 'search/repositories.html'

    def __init__(self, *args, **kwargs):
        """
        Use our own form and save a "search key" for theses searches
        to be used for more recents/popular
        """
        kwargs['form_class'] = RepositorySearchForm
        kwargs['search_key'] = 'repositories'
        super(RepositorySearchView, self).__init__(*args, **kwargs)

    def extra_context(self):
        """
        Add more recents and populars
        """
        context = dict(
            most_popular = SavedSearch.objects.most_popular(search_key='repositories')[:20],
            most_recent = SavedSearch.objects.most_recent(search_key='repositories')[:20],
        )
        if self.request.user and self.request.user.is_authenticated():
            context['user_most_recent'] = SavedSearch.objects.most_recent(
                search_key='repositories', user=self.request.user)[:20]

        return context


class AccountSearchView(PurePaginationSearchView):
    """
    Class based view to handle search of accounts
    """
    __name__ = 'AccountSearchView'
    template = 'search/accounts.html'

    def __init__(self, *args, **kwargs):
        """
        Use our own form and save a "search key" for theses searches
        """
        kwargs['form_class'] = AccountSearchForm
        kwargs['search_key'] = 'accounts'
        super(AccountSearchView, self).__init__(*args, **kwargs)
