# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.http import Http404
from django.db.models import Q

from haystack.query import SQ, SearchQuerySet, EmptySearchQuerySet
from haystack.views import RESULTS_PER_PAGE
from pure_pagination import Paginator, InvalidPage

from core.models import Repository, Account

class CannotHandleException(Exception):
    pass

class _Filter(object):
    """
    An abstract default filter for all
    """

    def __init__(self, query_filter, search):
        """
        Create the filter and save the query_filter
        """
        super(_Filter, self).__init__()
        self.query_filter = query_filter
        self.search = search
        self.request = search.request

    def original_filter(self):
        """
        Compute the original filter
        """
        return self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Strip the filter and return it
        """
        if not query_filter:
            return ''
        try:
            return query_filter.strip()
        except:
            return ''

    @classmethod
    def handle(cls, search):
        """
        Return a new filter or raise CannotHandleException, after
        tried to get a tag from the filter
        """
        query_filter = cls.parse_filter(search.query_filter, search)
        return cls(query_filter, search)

    def apply(self, queryset):
        """
        Apply the current filter on the givent queryset for the current search
        and return an updated queryset
        If the search is emtpy, we return directly all the objects,
        else we apply the filter on ids for the current search
        """
        if isinstance(queryset, EmptySearchQuerySet):
            return self.get_objects()
        else:
            ids = list(self.get_ids())
            return queryset.filter(django_id__in=ids)

    def get_queryset_filter(self):
        """
        To be implemented in sublcasses
        """
        return Q()

    def get_manager(self):
        """
        Return the manager to use for the filter
        If the user is authenticated, use the manager including deleted objects
        """
        if self.search.check_user():
            return self.search.model.for_user_list
        else:
            return self.search.model.for_user

    def get_queryset(self):
        """
        Return the queryset on the search's model, filtered
        """
        return self.get_manager().filter(
                self.get_queryset_filter()
            )

    def get_ids(self):
        """
        Get the filtered queryset and return the ids (a queryset, in fact)
        """
        return self.get_queryset().values_list('id', flat=True)

    def get_objects(self):
        """
        Get the filtered queryset and return the objects (a queryset, in fact)
        """
        return self.get_queryset()


class NoFilter(_Filter):
    """
    A filter... without filter
    """

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if we don't have a filter
        """
        query_filter = super(NoFilter, cls).parse_filter(query_filter, search)
        if query_filter:
            raise CannotHandleException
        return None

    def original_filter(self):
        """
        Return an empty filter
        """
        return ''

    def apply(self, queryset):
        """
        No filter, return all
        """
        return queryset


class _TagFilter(_Filter):
    """
    An abstract filter for all tags
    """

    def original_filter(self):
        return 'tag:' + self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is a tag and return it
        """
        if not query_filter.startswith('tag:'):
            raise CannotHandleException
        return query_filter[4:]

    def get_queryset_filter(self):
        return Q(**{
            'privatetagged%s__owner' % self.search.model_name: self.request.user,
            'privatetagged%s__tag__slug' % self.search.model_name: self.query_filter,
        })


class SimpleTagFilter(_TagFilter):
    """
    A filter for simple tags (not flags, places, projects...)
    """
    pass


class _PrefixedTagFilter(_TagFilter):
    """
    A abstract filter for managing filter starting with a prefix
    """

    def original_filter(self):
        return 'tag:' + self.prefix + self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is a tag and starts with a prefix, and return the
        tag
        """
        tag = super(_PrefixedTagFilter, cls).parse_filter(query_filter, search)
        if not tag.startswith(cls.prefix):
            raise CannotHandleException
        return tag


class PlaceFilter(_PrefixedTagFilter):
    """
    A filter for projects (tags starting with @)
    """
    prefix = '@'


class ProjectFilter(_PrefixedTagFilter):
    """
    A filter for projects (tags starting with #)
    """
    prefix = '#'


class FlagFilter(_TagFilter):
    """
    A filter for specific flags, defined in allowed
    """
    allowed = ('starred', 'check-later')

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is an allowed flag and return it
        """
        tag = super(FlagFilter, cls).parse_filter(query_filter, search)
        if tag not in cls.allowed:
            raise CannotHandleException
        return tag


class NotedFilter(_Filter):
    """
    A filter for noted objects
    """

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is exactly "noted"
        """
        query_filter = super(NotedFilter, cls).parse_filter(query_filter, search)
        if query_filter != 'noted':
            raise CannotHandleException
        return query_filter


class UserObjectListFilter(_Filter):
    """
    A filter for list of a loggued user
    """

    # all allowed filters for each model, with the matching queryset main part
    allowed = dict(
        account = dict(
            following = 'followers',
            followers = 'following',
        ),
        repository = dict(
            following = 'followers',
            owned = 'owner',
        )
    )

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is an allowed one
        """
        if not search.check_user():
            raise CannotHandleException
        query_filter = super(UserObjectListFilter, cls).parse_filter(query_filter, search)
        if query_filter not in cls.allowed[search.model_name]:
            raise CannotHandleException
        return query_filter

    def get_queryset_filter(self):
        """
        Return a filter on a list for the current user
        """
        part = self.allowed[self.search.model_name][self.query_filter]
        return Q(**{'%s__user' % part: self.request.user})


# all valid filter, ordered
FILTERS = (UserObjectListFilter, FlagFilter, ProjectFilter, PlaceFilter, SimpleTagFilter, NoFilter)
DEFAULT_FILTER = NoFilter


class Search(object):
    model = None
    search_key = None
    search_fields = None

    def __init__(self, request, results_per_page=None):
        """
        Create the search object, getting parameters from request
        """
        super(Search, self).__init__()

        # init fields
        self.request = request
        self.query = self.request.REQUEST.get('q', None)
        self.query_filter = self.request.REQUEST.get('filter', None)

        self.model_name = self.model.model_name
        self.results_per_page = results_per_page or RESULTS_PER_PAGE

        self.results = None

        # get options and filter
        self.filter = self.get_filter()
        self.options = self.get_options()


    @classmethod
    def get_for_request(cls, request):
        """
        Return either a RepositorySearch or AccountSearch
        """
        if request.REQUEST.get('type', 'repositories') == 'people':
            return AccountSearch(request)
        else:
            return RepositorySearch(request)

    def _request_param(self, name, default=None, post_first=True):
        """
        Try to retrieve a parameter from the request
        """
        first_dict, second_dict = self.request.POST, self.request.GET
        if not post_first:
            first_dict, second_dict = second_dict, first_dict
        return first_dict.get(name, second_dict.get(name, default))

    def get_filter(self):
        """
        Find a good filter object for query string
        Raise CannotHandleException if no filter found
        """
        filter_obj = None
        for filter_cls in FILTERS:
            try:
                filter_obj = filter_cls.handle(self)
            except:
                continue
            else:
                break
        if not filter_obj:
            return DEFAULT_FILTER(self.query_filter, self)
        return filter_obj

    def get_options(self):
        """
        Return a dict with all options
        """
        return {}

    def parse_keywords(self, query_string):
        """
        Take a query string (from userr) and parse it to have a list of keywords.
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

    def make_query(self, fields, keywords, queryset=None):
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

    def get_search_queryset(self):
        """
        Return the results for this search
        """
        if self.query:
            keywords = self.parse_keywords(self.query)
            queryset = self.make_query(self.search_fields, keywords)

            queryset = queryset.models(self.model)

            return queryset
        else:
            return EmptySearchQuerySet()

    def apply_filter(self, queryset):
        """
        Apply the current filter to the queryset
        TODO : really do something !
        """
        if self.filter:
            return self.filter.apply(queryset)
        return queryset

    def apply_options(self, queryset):
        """
        Apply some options to the queryset
        Do nothing by default
        """
        return queryset

    def paginate(self, results):
        """
        Use django-pure-pagination to return the wanted page only
        """
        paginator = Paginator(results, self.results_per_page, request=self.request)

        try:
            page = paginator.page(self.request.REQUEST.get('page', 1))
        except InvalidPage:
            raise Http404

        return page

    def update_results(self):
        """
        Calculate te results
        """
        self.results = self.paginate(
            self.apply_options(
                self.apply_filter(
                    self.get_search_queryset()
                )
            )
        )

    def get_results(self, force_update=False):
        """
        Return the final page of results
        """
        if force_update or self.results is None:
            self.update_results()
        return self.results

    def check_user(self):
        """
        Return True if the user is authenticated and active, or return False
        """
        if not hasattr(self, '_check_user_cache'):
            try:
                self._check_user_cache = self.request.user.is_authenticated() and self.request.user.is_active
            except:
                self._check_user_cache = False
        return self._check_user_cache



class RepositorySearch(Search):
    """
    A search in repositories
    """
    model = Repository
    model_name = 'repository'
    search_key = 'repositories'
    search_fields = ('slug', 'slug_sort', 'name', )

    def get_options(self):
        """
        Get the "show forks" option
        """
        options = super(RepositorySearch, self).get_options()
        options.update(dict(
            show_forks = 'y' if self.request.REQUEST.get('show-forks', 'n') == 'y' else False,
        ))
        return options

    def apply_options(self, queryset):
        """
        Apply the "show forks" option
        """
        queryset = super(RepositorySearch, self).apply_options(queryset)

        if isinstance(queryset, EmptySearchQuerySet):
            return queryset

        if not self.options.get('show_forks', False):
            queryset = queryset.exclude(is_fork=True)

        return queryset



class AccountSearch(Search):
    """
    A search in accounts
    """
    model = Account
    model_name = 'account'
    search_key = 'accounts'
    search_fields = ('project', 'slug', 'slug_sort', 'name', 'description', 'readme',)
