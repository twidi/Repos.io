from django.db import models

from taggit.models import ItemBase, TagBase

from core.utils import slugify as core_slugify

class Tag(TagBase):

    official = models.BooleanField(default=False)

    def slugify(self, tag, i=None):
        slug = core_slugify(tag)
        if i is not None:
            slug += "_%d" % i
        return slug

class BaseTaggedItem(ItemBase):
    tag = models.ForeignKey(Tag, related_name="%(app_label)s_%(class)s_items")

    class Meta:
        abstract = True

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
    class Meta:
        abstract = True

class PublicTaggedAccount(PublicTaggedItem):
    content_object = models.ForeignKey('core.Account')

class PublicTaggedRepository(PublicTaggedItem):
    content_object = models.ForeignKey('core.Repository')

#class PrivateTaggedItem(BaseTaggedItem):
#    class Meta:
#        abstract = True
#
#class PrivateTaggedAccount(PrivateTaggedItem):
#    content_object = models.ForeignKey(Account)
#
#class PrivateTaggedRepository(PrivateTaggedItem):
#    content_object = models.ForeignKey(Repository)
