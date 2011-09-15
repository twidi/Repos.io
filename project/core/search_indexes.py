from datetime import datetime
import math

from django.conf import settings

from haystack.indexes import *
from haystack import site

from core.models import Account, Repository

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
    internal_score = IntegerField(model_attr='score', indexed=False)

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

    def prepare(self, obj):
        """
        Use the object's score to calculate the boost
        """
        data = super(CoreIndex, self).prepare(obj)
        data['boost'] = math.log10(max(obj.score, 5) / 5.0) / 2.5 + 0.7
        return data

    # limit index to 1000 objects in debug mode
    if settings.DEBUG:
        def index_queryset(self):
            qs = super(CoreIndex, self).index_queryset()
            return qs.filter(id__lt=1001)

class AccountIndex(CoreIndex):
    """
    Search index for Account objects
    """
    renderer_links = CharField(use_template=True, indexed=False)

site.register(Account, AccountIndex)

class RepositoryIndex(CoreIndex):
    """
    Search index for Repository objects
    """
    project = CharField(model_attr='project')
    description = CharField(model_attr='description', null=True)
    readme = CharField(model_attr='readme', null=True)
    renderer_description = CharField(use_template=True, indexed=False)
    renderer_owner = CharField(use_template=True, indexed=False)
    renderer_updated = CharField(use_template=True, indexed=False)
    owner_slug_sort = CharField(null=True)
    official_modified_sort = DateTimeField(model_attr='official_modified', null=True)

    def prepare_owner_slug_sort(self, obj):
        if obj.owner_id:
            return self._prepare_slug_sort(obj.owner.slug_sort)
        return None

site.register(Repository, RepositoryIndex)
