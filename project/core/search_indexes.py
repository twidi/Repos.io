from datetime import datetime

from django.conf import settings

from haystack.indexes import *
from haystack import site

from core.models import Account, Repository

IS_WHOOSH = getattr(settings, 'HAYSTACK_SEARCH_ENGINE', None) == 'whoosh'

class CoreIndex(SearchIndex):
    """
    Base search index, used for core models
    """
    text = CharField(document=True, use_template=True)
    slug = CharField(model_attr='slug')
    slug_normalized = CharField(model_attr='slug_sort')
    slug_sort = CharField()
    name = CharField(model_attr='name', null=True)
    modified = DateTimeField(model_attr='modified')
    renderer_main = CharField(use_template=True, indexed=False)
    get_absolute_url = CharField(model_attr='get_absolute_url', indexed=False)

    def get_updated_field(self):
        """
        Use the `modified` field to only updates new objects
        """
        return 'modified'

    def _prepare_slug_sort(self, slug):
        """
        Replace `-` characters by `_` to have one entire worl instead of many
        in search engines, better for correct sorting
        """
        return slug.replace('-', '_')

    def prepare_slug_sort(self, obj):
        return self._prepare_slug_sort(obj.slug_sort)

    # HACK : every sort fields must be filled for EVERY entries  for sorting in whoosh !
    # https://github.com/toastdriven/django-haystack/issues/418#issuecomment-2065707
    if IS_WHOOSH:
        owner_slug_sort = CharField(null=True)
        official_modified_sort = DateTimeField(null=True)

        def prepare_owner_slug_sort(self, obj):
            if getattr(obj, 'owner_id', False):
                return self._prepare_slug_sort(obj.owner.slug_sort)
            return '__no_owner__'

        def prepare_official_modified_sort(self, obj):
            if getattr(obj, 'official_modified', False):
                return obj.official_modified
            return datetime.min

class AccountIndex(CoreIndex):
    renderer_links = CharField(use_template=True, indexed=False)

site.register(Account, AccountIndex)

class RepositoryIndex(CoreIndex):
    project = CharField(model_attr='project')
    description = CharField(model_attr='description', null=True)
    readme = CharField(model_attr='readme', null=True)
    renderer_description = CharField(use_template=True, indexed=False)
    renderer_owner = CharField(use_template=True, indexed=False)
    renderer_updated = CharField(use_template=True, indexed=False)

    if not IS_WHOOSH:
        owner_slug_sort = CharField(null=True)
        official_modified_sort = DateTimeField(model_attr='official_modified', null=True)

        def prepare_owner_slug_sort(self, obj):
            if obj.owner_id:
                return self._prepare_slug_sort(obj.owner.slug_sort)
            return None

site.register(Repository, RepositoryIndex)
