from haystack.indexes import *
from haystack import site
from core.models import Account, Repository

class AccountIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
    slug = CharField(model_attr='slug')
    slug_sort = CharField(model_attr='slug_sort')
    name = CharField(model_attr='name', null=True)
    renderer = CharField(use_template=True, indexed=False)
site.register(Account, AccountIndex)

class RepositoryIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
    slug = CharField(model_attr='slug')
    slug_sort = CharField(model_attr='slug_sort')
    name = CharField(model_attr='name', null=True)
    project = CharField(model_attr='project')
    description = CharField(model_attr='description', null=True)
    readme = CharField(model_attr='readme', null=True)
    renderer = CharField(use_template=True, indexed=False)
site.register(Repository, RepositoryIndex)
