# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from taggit.managers import TaggableManager as BaseTaggableManager, _TaggableManager as _BaseTaggableManager
from taggit.utils import require_instance_manager

class TaggableManager(BaseTaggableManager):
    """
    We must subclass it to use our own manager
    """
    def __init__(self, *args, **kwargs):
        """
        A related name can now be set
        """
        related_name = kwargs.pop('related_name', None)
        super(TaggableManager, self).__init__(*args, **kwargs)
        if related_name:
            self.rel.related_name = related_name

    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("%s objects need to have a primary key value "
                "before you can access their tags." % model.__name__)
        manager = _TaggableManager(
            through=self.through, model=model, instance=instance
        )
        return manager


def prepare_tag(tag):
    return tag.strip().lower()


class _TaggableManager(_BaseTaggableManager):
    """
    Manager to use add, set... with a weight for each tag
    """

    def _lookup_kwargs(self, **filters):
        """
        It's possible to filter by other fields
        """
        result = self.through.lookup_kwargs(self.instance)
        result.update(filters)
        return result

    @require_instance_manager
    def add(self, tags, **filters):
        """
        Add a list of tags.
        We consider the SLUG of each tag
        Each tag can be :
        - a Tag object, eventually with a weight added field
        - a tuple with a tag and a weight, the tag can be:
            - a Tag object (weight will be the default one)
            - a string
        - a string (weight will be the default one)
        """
        if isinstance(tags, dict):
            tags = tags.items()

        obj_tags = {}
        str_tags = {}

        for tag in tags:
            if isinstance(tag, self.through.tag_model()):
                obj_tags[prepare_tag(tag.name)] = (tag, getattr(tag, 'weight', None))
            elif isinstance(tag, (tuple, list)):
                if isinstance(tag[0], self.through.tag_model()):
                    obj_tags[prepare_tag(tag[0].name)] = tag
                elif isinstance(tag[0], basestring):
                    str_tags[prepare_tag(tag[0])] = tag[1]
            elif isinstance(tag, basestring):
                str_tags[prepare_tag(tag)] = None

        # If str_tags has 0 elements Django actually optimizes that to not do a
        # query.  Malcolm is very smart.
        existing = self.through.tag_model().objects.filter(
            name__in=str_tags.keys()
        )

        dict_existing = dict((t.name, t) for t in existing)
        for tag in str_tags.keys():
            if tag in dict_existing:
                obj_tags[tag] = (dict_existing[tag], str_tags[tag])
                del str_tags[tag]

        # add new str_tags
        for new_tag, weight in str_tags.items():
            obj_tags[new_tag] = (
                self.through.tag_model().objects.create(name=new_tag),
                weight
            )

        for slug, tag in obj_tags.items():
            defaults = {}
            if tag[1]:
                defaults['weight'] = tag[1]

            params = dict(tag=tag[0], defaults=defaults)
            params.update(self._lookup_kwargs(**filters))

            tagged_item, created = self.through.objects.get_or_create(**params)
            if not created and tagged_item.weight != tag[1]:
                tagged_item.weight = tag[1]
                tagged_item.save()

    @require_instance_manager
    def set(self, tags, **filters):
        self.clear(**filters)
        self.add(tags, **filters)

    @require_instance_manager
    def remove(self, tags, **filters):
        str_tags = set()
        for tag in tags:
            if isinstance(tag, (tuple, list)):
                tag = tag[0]
            if isinstance(tag, self.through.tag_model()):
                tag = tag.name
            str_tags.add(tag)

        self.through.objects.filter(**self._lookup_kwargs(**filters)).filter(
            tag__name__in=str_tags).delete()

    @require_instance_manager
    def clear(self, **filters):
        self.through.objects.filter(**self._lookup_kwargs(**filters)).delete()
