# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.db.models import Q
from django.conf import settings

from haystack.query import SQ, SearchQuerySet, EmptySearchQuerySet
from haystack.models import SearchResult

from core.models import Repository, Account
from utils.sort import prepare_sort

class CannotHandleException(Exception):
    pass

class CoreSearchResult(SearchResult):
    pass

class RepositoryResult(CoreSearchResult):
    model_name_plural = Repository.model_name_plural
    content_type = Repository.content_type
    search_type = Repository.search_type

class AccountResult(CoreSearchResult):
    model_name_plural = Account.model_name_plural
    content_type = Account.content_type
    search_type = Account.search_type

class _Filter(object):
    """
    An abstract default filter for all
    """
    only = dict(
        account = ('id', 'backend', 'status', 'slug', 'modified'),
        repository = ('id', 'backend', 'status', 'slug', 'project', 'modified'),
    )
    default_sort = None

    def __init__(self, query_filter, search):
        """
        Create the filter and save the query_filter
        """
        super(_Filter, self).__init__()
        self.query_filter = query_filter
        self.search = search
        # if the search has a query, the default sort is the solr one
        if search.query:
            self.default_sort = None

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
            ids = list(self.get_ids()[:settings.SOLR_MAX_IN])
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
            return self.search.model.objects
        else:
            return self.search.model.objects.exclude(deleted=True)

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
        We only need the id (status is required by core/models) because we
        directly load a cached template
        """
        return self.get_queryset().only(*self.only[self.search.model_name])


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
    default_sort = 'name'

    def original_filter(self):
        return 'tag:' + self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is a tag and return it
        """
        if not search.check_user():
            raise CannotHandleException
        if not query_filter.startswith('tag:'):
            raise CannotHandleException
        return query_filter[4:]

    def get_queryset_filter(self):
        return Q(**{
            'privatetagged%s__owner' % self.search.model_name: self.search.user,
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
    default_sort = 'name'

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is exactly "noted"
        """
        if not search.check_user():
            raise CannotHandleException
        query_filter = super(NotedFilter, cls).parse_filter(query_filter, search)
        if query_filter != 'noted':
            raise CannotHandleException
        return query_filter

    def get_queryset_filter(self):
        """
        Return only objects with a note
        """
        return Q(note__author=self.search.user)


class TaggedFilter(_Filter):
    """
    An abstract filter for tagged objects
    """
    default_sort = 'name'

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is exactly "tagged"
        """
        if not search.check_user():
            raise CannotHandleException
        query_filter = super(TaggedFilter, cls).parse_filter(query_filter, search)
        if query_filter != 'tagged':
            raise CannotHandleException
        return query_filter

    def get_queryset_filter(self):
        return Q(**{
            'privatetagged%s__owner' % self.search.model_name: self.search.user,
        })

    def get_queryset(self):
        qs = super(TaggedFilter, self).get_queryset()
        qs = qs.exclude(**{
                'privatetagged%s__tag__slug__in' % self.search.model_name: ('check-later', 'starred'),
            })
        return qs.distinct()


class UserObjectListFilter(_Filter):
    """
    A filter for list of a loggued user
    """
    default_sort = 'name'

    # all allowed filters for each model, with the matching queryset main part
    allowed = dict(
        account = dict(
            following = 'followers__user',
            followers = 'following__user',
            accounts = 'user',
        ),
        repository = dict(
            following = 'followers__user',
            owned = 'owner__user',
            contributed = 'contributors__user',
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
        return Q(**{part: self.search.user})


class ObjectRelativesFilter(_Filter):
    """
    A filter for a list of objects relatives to an object
    """
    default_sort = 'score'

    allowed = dict(
        account = ('following', 'followers', 'repositories', 'contributing'),
        repository = ('followers', 'contributors', 'forks')
    )

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is an allowed one
        """
        if not search.base:
            raise CannotHandleException
        query_filter = super(ObjectRelativesFilter, cls).parse_filter(query_filter, search)
        if query_filter not in cls.allowed[search.base.model_name]:
            raise CannotHandleException
        return query_filter

    def get_queryset(self):
        """
        Return a filter of on a list for the current base object
        """
        queryset = getattr(self.search.base, self.query_filter).all()
        #if self.search.base.model_name == 'account' and self.search.model_name == 'repository'
        return queryset


# all valid filter, ordered
FILTERS = (ObjectRelativesFilter, UserObjectListFilter, NotedFilter, TaggedFilter, FlagFilter, ProjectFilter, PlaceFilter, SimpleTagFilter, NoFilter)
DEFAULT_FILTER = NoFilter


class Search(object):
    model = None
    model_name = None
    search_key = None
    search_fields = None
    search_params = ('q', 'filter', 'order')
    allowed_options = ()

    order_map = dict(db={}, solr={})

    def __init__(self, params, user=None):
        """
        Create the search object
        """
        super(Search, self).__init__()

        # init fields
        self.params = params
        self.user = user

        self.query = self.get_param('q')
        self.query_filter = self.get_param('filter')
        self.query_order = self.get_param('order')

        self.model_name = self.model.model_name

        self.results = None

        # get search parameters
        self.base = self.get_base()
        self.filter = self.get_filter()
        self.options = self.get_options()
        self.order = self.get_order()

    @staticmethod
    def get_class(search_type):
        """
        Return the correct search class for the given type
        """
        if search_type == 'people':
            return AccountSearch
        elif search_type == 'repositories':
            return RepositorySearch

    @staticmethod
    def get_for_params(params, user=None):
        """
        Return either a RepositorySearch or AccountSearch
        """
        cls = Search.get_class(params.get('type', 'repositories'))
        return cls(params, user)

    @staticmethod
    def get_params_from_request(request, search_type, ignore=None):
        """
        Get some params from the request, if they are not already defined (in ignore)
        """
        cls = Search.get_class(search_type)

        all_params = list(cls.search_params + cls.allowed_options)
        all_params += ['direct-%s' % param for param in all_params]

        params = {}
        for param in all_params:
            if ignore and param in ignore:
                continue
            if param not in request.REQUEST:
                continue
            params[param] = request.REQUEST[param]
        return params

    def get_param(self, name, default=''):
        """
        Return the value of the `name` field in the parameters of the current
        search, stripped. If we have a value for the same parameter but with a
        name prefixed with 'direct-', use it
        """
        return self.params.get(
            'direct-%s' % name,
            self.params.get(
                name,
                default
            )
        ).strip()

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
        options = {}
        for option in self.allowed_options:
            options[option] = 'y' if self.get_param(option, 'n') == 'y' else False
        return options

    def get_base(self):
        """
        Verify and save the base object if we have one
        """
        base = self.params.get('base', None)
        if base and isinstance(base, (Account, Repository)):
            return base
        return None

    def get_order(self):
        """
        Get the correct order for the current search
        """
        order_map_type = 'solr' if self.query else 'db'
        result = prepare_sort(
            self.query_order,
            self.order_map[order_map_type],
            self.filter.default_sort,
            False
        )
        if not result['key']:
            result['key'] = ''
        return result

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
        only_exclude = True

        for keyword in keywords:
            exclude = False
            if keyword.startswith('-') and len(keyword) > 1:
                exclude = True
                keyword = keyword[1:]
            else:
                only_exclude = False

            keyword = queryset.query.clean(keyword)

            q_keyword = None

            for field in fields:

                q_field = SQ(**{ field: keyword })

                if q_keyword:
                    q_keyword = q_keyword | q_field
                else:
                    q_keyword = q_field

            if exclude:
                q_keyword = ~ q_keyword

            if q:
                q = q & q_keyword
            else:
                q = q_keyword

        if q:
            if only_exclude and len(keywords) > 1:
                # it seems that solr cannot manage only exclude when we have many of them
                # so we AND a query that we not match : the same as for ".models(self.model)"
                q = SQ(django_ct = 'core.%s' % self.model_name) & q
            return queryset.filter(q)
        else:
            return queryset

    def get_search_queryset(self):
        """
        Return the results for this search
        We only need the id because we
        directly load a cached template
        """
        if self.query:
            keywords = self.parse_keywords(self.query)
            queryset = self.make_query(self.search_fields, keywords)

            queryset = queryset.models(self.model).only('id', 'get_absolute_url', 'modified')

            return queryset.result_class(self.result_class)
        else:
            return EmptySearchQuerySet()

    def apply_filter(self, queryset):
        """
        Apply the current filter to the queryset
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

    def apply_order(self, queryset):
        """
        Apply the current order to the query set
        """
        if self.order['db_sort']:
            return queryset.order_by(self.order['db_sort'])
        return queryset

    def update_results(self):
        """
        Calculate te results
        """
        self.results = self.apply_order(
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
                self._check_user_cache = self.user and self.user.is_authenticated() and self.user.is_active
            except:
                self._check_user_cache = False
        return self._check_user_cache

    def content_template(self):
        """
        Return the template to use for this search's results
        """
        return 'front/%s_content.html' % self.model_name

    def is_default(self):
        """
        Return True if the Search is in a default status (no filter, options, order, query)
        """

        if self.query:
            return False
        if not self.base and self.filter.original_filter():
            return False
        sort_key = self.order.get('key', None)
        if sort_key and sort_key != self.filter.default_sort:
            return False
        if any(self.options.values()):
            return False
        return True


class RepositorySearch(Search):
    """
    A search in repositories
    """
    model = Repository
    model_name = 'repository'
    search_key = 'repositories'
    search_fields = ('project', 'slug', 'slug_sort', 'name', 'description', 'readme',)
    allowed_options = ('show_forks', 'is_owner',)
    result_class = RepositoryResult

    order_map = dict(
        db = dict(
            name = 'slug_sort',
            score = '-score',
            owner = 'owner__slug_sort',
            updated = '-official_modified',
            owner_score = '-owner__score',
        ),
        solr = dict(
            name = 'slug_sort',
            score = '-internal_score',
            owner = 'owner_slug_sort',
            updated = '-official_modified_sort',
            owner_score = '-owner_internal_score',
        ),
    )

    def apply_options(self, queryset):
        """
        Apply the "show forks" option
        """
        queryset = super(RepositorySearch, self).apply_options(queryset)

        if isinstance(queryset, EmptySearchQuerySet):
            return queryset

        if not self.options.get('show_forks', False):
            queryset = queryset.exclude(is_fork=True)

        if self.base and self.base.model_name == 'account' and self.options.get('is_owner', False):
            queryset = queryset.filter(owner=self.base.pk)

        return queryset


class AccountSearch(Search):
    """
    A search in accounts
    """
    model = Account
    model_name = 'account'
    search_key = 'accounts'
    search_fields = ('slug', 'slug_sort', 'name', 'all_public_tags')
    result_class = AccountResult

    order_map = dict(
        db = dict(
            name = 'slug_sort',
            score = '-score',
        ),
        solr = dict(
            name = 'slug_sort',
            score = '-internal_score',
        ),
    )
