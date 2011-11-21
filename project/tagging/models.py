# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.db import models
from django.contrib.auth.models import User

from taggit.models import ItemBase, TagBase

from core.core_utils import slugify as core_slugify
from tagging.managers import prepare_tag

class Tag(TagBase):

    official = models.BooleanField(default=False)

    class Meta:
        ordering = ['slug',]

    def slugify(self, tag, i=None):
        slug = core_slugify(tag)
        if i is not None:
            slug += "_%d" % i
        return slug

    def save(self, *args, **kwargs):
        self.name = prepare_tag(self.name)
        super(Tag, self).save(*args, **kwargs)

class BaseTaggedItem(ItemBase):
    weight = models.FloatField(blank=True, null=True, default=1)

    class Meta:
        abstract = True
        ordering = ('-weight', 'tag__slug',)

    @classmethod
    def tags_for(cls, model, instance=None):
        if instance is not None:
            return cls.tag_model().objects.filter(**{
                '%s__content_object' % cls.tag_relname(): instance
            })
        return cls.tag_model().objects.filter(**{
            '%s__content_object__isnull' % cls.tag_relname(): False
        }).distinct()

class PublicTaggedItem(BaseTaggedItem):
    class Meta(BaseTaggedItem.Meta):
        abstract = True

class PublicTaggedAccount(PublicTaggedItem):
    tag = models.ForeignKey(Tag, related_name="public_account_tags")
    content_object = models.ForeignKey('core.Account')

class PublicTaggedRepository(PublicTaggedItem):
    tag = models.ForeignKey(Tag, related_name="public_repository_tags")
    content_object = models.ForeignKey('core.Repository')

class PrivateTaggedItem(BaseTaggedItem):
    owner = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_items")

    class Meta(BaseTaggedItem.Meta):
        abstract = True

class PrivateTaggedAccount(PrivateTaggedItem):
    tag = models.ForeignKey(Tag, related_name="private_account_tags")
    content_object = models.ForeignKey('core.Account')

class PrivateTaggedRepository(PrivateTaggedItem):
    tag = models.ForeignKey(Tag, related_name="private_repository_tags")
    content_object = models.ForeignKey('core.Repository')

def all_official_tags():
    """
    Return (and cache) the list of all official tags (as a set of slugs)
    """
    if not all_official_tags._cache:
        all_official_tags._cache = set(Tag.objects.filter(official=True).values_list('slug', flat=True))
    return all_official_tags._cache
all_official_tags._cache = None
