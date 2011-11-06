from django.http import Http404

from haystack.forms import SearchForm
from haystack.query import SQ, SearchQuerySet, EmptySearchQuerySet
from pure_pagination import Paginator, InvalidPage
from saved_searches.views import SavedSearchView as BaseSearchView
from saved_searches.models import SavedSearch

from core.models import Account, Repository
from utils.sort import prepare_sort

def parse_keywords(query_string):
    """
    Take a query string (think browser) and parse it to have a list of keywords.
    If many words are between two double-quotes, they are considered as one
    keyword.
    """
    qs = SearchQuerySet()
    keywords = []
    # Pull out anything wrapped in quotes and do an exact match on it.
    open_quote_position = None
    non_exact_query = query_string
    for offset, char in enumerate(query_string):
        if char == '"':
            if open_quote_position != None:
                current_match = non_exact_query[open_quote_position + 1:offset]
                if current_match:
                    keywords.append(qs.query.clean(current_match))
                non_exact_query = non_exact_query.replace('"%s"' % current_match, '', 1)
                open_quote_position = None
            else:
                open_quote_position = offset
    # Pseudo-tokenize the rest of the query.
    keywords += non_exact_query.split()

    return keywords

    result = []
    for keyword in keywords:
        result.append(qs.query.clean(keyword))

    return result

def make_query(fields, keywords, queryset=None):
    """
    Create the query for haystack for searching in `fields ` for documents
    with `keywords`. All keywords are ANDed, and if a keyword starts with a "-"
    all document with it will be excluded.
    """
    if not keywords or not fields:
        return EmptySearchQuerySet()

    if not queryset:
        queryset = SearchQuerySet()

    q = None
    for field in fields:
        q_field = None
        for keyword in keywords:
            exclude = False
            if keyword.startswith('-') and len(keyword) > 1:
                exclude = True
                keyword = keyword[1:]

            q_tmp = SQ(**{field: queryset.query.clean(keyword)})

            if exclude:
                q_tmp = ~ q_tmp

            if q_field:
                q_field = q_field & q_tmp
            else:
                q_field = q_tmp

        if q:
            q = q | q_field
        else:
            q = q_field

    if q:
        return queryset.filter(q)
    else:
        return queryset

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
        kwargs['form_class'] = SearchForm
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
        query = self.get_query()
        if query:
            keywords = parse_keywords(self.get_query())
            queryset = make_query(self.search_fields, keywords)

            queryset = queryset.models(self.model)

            sort = self.get_sort()
            if sort and sort['db_sort']:
                queryset = queryset.order_by(sort['db_sort'])

            return queryset
        else:
            return EmptySearchQuerySet()

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
    search_fields = ('project', 'slug', 'slug_sort', 'name', 'description', 'readme',)

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

        if self.request.GET.get('show-forks', False) == 'y':
            context['show_forks'] = 'y'

        return context

    def get_results(self):
        """
        Filter with is_fork
        """
        result = super(RepositorySearchView, self).get_results()

        if not isinstance(result, EmptySearchQuerySet):
            show_forks = self.request.GET.get('show-forks', False) == 'y'
            if not show_forks:
                result = result.exclude(is_fork=True)

        return result

    def save_search(self, page):
        """
        Do not save if the sort order is not the default one or if a filter is applied
        """
        if self.request.GET.get('show-forks', False) == 'y':
            return
        sort = self.get_sort()
        if sort and sort['db_sort']:
            return
        return super(RepositorySearchView, self).save_search(page)


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
    search_fields = ('slug', 'slug_sort', 'name', )
