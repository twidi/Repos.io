from django.http import Http404

from pure_pagination import Paginator, InvalidPage
from saved_searches.views import SavedSearchView as BaseSearchView
from saved_searches.models import SavedSearch

from core.models import Account, Repository
from utils.sort import prepare_sort

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

class CoreSearchView(PurePaginationSearchView):
    """
    Class based view to handle search on core's objects
    """
    search_key = None
    model = None
    sort_map = {}

    def __init__(self, *args, **kwargs):
        """
        Set a "search key" for theses searches to be used for more recents/popular
        """
        kwargs['search_key'] = self.search_key
        super(CoreSearchView, self).__init__(*args, **kwargs)

    def get_sort(self):
        """
        Prepare (with validiti check) sorting key
        """
        if not hasattr(self.request, '_haystack_sort'):
            self.request._haystack_sort = None
            if self.sort_map:
                sort_key = self.request.GET.get('sort_by', None)
                self._haystack_sort = prepare_sort(
                    key = sort_key,
                    sort_map = self.sort_map,
                    default = None,
                    default_reverse = False
                )
        return self._haystack_sort

    def get_results(self):
        """
        Limit to a model, and sort if needed
        """
        results = super(CoreSearchView, self).get_results()

        queryset = results.models(self.model)

        sort = self.get_sort()
        if sort and sort['db_sort']:
            queryset = queryset.order_by(sort['db_sort'])

        return queryset

    def extra_context(self):
        """
        Add sorting infos in context
        """
        context = {}
        context.update(super(CoreSearchView, self).extra_context())
        context['sort'] = self.get_sort()

        return context


class RepositorySearchView(CoreSearchView):
    """
    Class based view to handle search of repositories
    """
    __name__ = 'RepositorySearchView'
    template = 'search/repositories.html'
    search_key = 'repositories'
    model = Repository
    sort_map = dict(
        name = 'slug_sort',
        owner = 'owner_slug_sort',
        updated = 'official_modified_sort',
    )

    def extra_context(self):
        """
        Add more recents and populars
        """
        context = {}
        context.update(super(RepositorySearchView, self).extra_context())
        context.update(dict(
            most_popular = SavedSearch.objects.most_popular(search_key='repositories')[:20],
            most_recent = SavedSearch.objects.most_recent(search_key='repositories')[:20],
        ))
        if self.request.user and self.request.user.is_authenticated():
            context['user_most_recent'] = SavedSearch.objects.most_recent(
                search_key='repositories', user=self.request.user)[:20]

        return context


class AccountSearchView(CoreSearchView):
    """
    Class based view to handle search of accounts
    """
    __name__ = 'AccountSearchView'
    template = 'search/accounts.html'
    search_key = 'accounts'
    model = Account
    sort_map = dict(
        name = 'slug_sort',
    )
