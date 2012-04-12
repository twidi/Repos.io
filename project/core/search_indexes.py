# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import re

from haystack.indexes import *
from haystack import site

from core.models import Account, Repository

SLUG_SORT_RE = re.compile(r'[^a-z]')

class CoreIndex(SearchIndex):
    """
    Base search index, used for core models
    """
    text = CharField(document=True, use_template=True)
    slug = CharField(model_attr='slug', boost=2)
    slug_normalized = CharField(model_attr='slug_sort')
    slug_sort = CharField()
    name = CharField(model_attr='name', null=True, boost=1.5)
    modified = DateTimeField(model_attr='modified')
    internal_score = IntegerField()
    get_absolute_url = CharField(model_attr='get_absolute_url', indexed=False)

    def get_updated_field(self):
        """
        Use the `modified` field to only updates new objects
        """
        return 'modified'

    def _prepare_slug_sort(self, slug):
        """
        Remove everything but letters, to have one entire worl instead of many
        in search engines, better for correct sorting
        """
        return SLUG_SORT_RE.sub('a', slug.replace('-', ''))

    def prepare_slug_sort(self, obj):
        return self._prepare_slug_sort(obj.slug_sort)

    def prepare_internal_score(self, obj):
        return obj.score or 0

    def prepare(self, obj):
        """
        Use the object's score to calculate the boost
        """
        data = super(CoreIndex, self).prepare(obj)
        data['boost'] = obj.score_to_boost()
        return data

class AccountIndex(CoreIndex):
    """
    Search index for Account objects
    """
    all_public_tags = CharField(null=True)

    def prepare_all_public_tags(self, obj):
        return ' '.join([tag.slug for tag in obj.all_public_tags()])

site.register(Account, AccountIndex)

class RepositoryIndex(CoreIndex):
    """
    Search index for Repository objects
    """
    project = CharField(model_attr='project', boost=2.5)
    description = CharField(model_attr='description', null=True)
    readme = CharField(model_attr='readme', null=True, boost=0.5)
    owner_slug_sort = CharField(null=True)
    official_modified_sort = DateTimeField(model_attr='official_modified', null=True)
    owner_id = IntegerField(model_attr='owner_id', null=True)
    is_fork = BooleanField(model_attr='is_fork', null=True)
    owner_internal_score = IntegerField()

    def prepare_owner_slug_sort(self, obj):
        if obj.owner_id:
            return self._prepare_slug_sort(obj.owner.slug_sort)
        return None

    def prepare_owner_internal_score(self, obj):
        if obj.owner_id and obj.owner.score:
            return obj.owner.score
        return 0

site.register(Repository, RepositoryIndex)
