from taggit.managers import TaggableManager as BaseTaggableManager, _TaggableManager as _BaseTaggableManager
from taggit.utils import require_instance_manager

class TaggableManager(BaseTaggableManager):
    """
    We must subclass it to use our own manager
    """
    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("%s objects need to have a primary key value "
                "before you can access their tags." % model.__name__)
        manager = _TaggableManager(
            through=self.through, model=model, instance=instance
        )
        return manager


class _TaggableManager(_BaseTaggableManager):
    """
    Manager to use add, set... with a weight for each tag
    """

    @require_instance_manager
    def add(self, tags):
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
                obj_tags[tag.slug] = (tag, getattr(tag, 'weight', None))
            elif isinstance(tag, (tuple, list)):
                if isinstance(tag[0], self.through.tag_model()):
                    obj_tags[tag[0].slug] = tag
                elif isinstance(tag[0], basestring):
                    str_tags[tag[0]] = tag[1]
            elif isinstance(tag, basestring):
                str_tags[tag] = None

        # If str_tags has 0 elements Django actually optimizes that to not do a
        # query.  Malcolm is very smart.
        existing = self.through.tag_model().objects.filter(
            slug__in=str_tags.keys()
        )

        dict_existing = dict((t.slug, t) for t in existing)
        for tag in str_tags.keys():
            if tag in dict_existing:
                obj_tags[tag] = (dict_existing[tag], str_tags[tag])
                del str_tags[tag]

        # add new str_tags
        for new_tag, weight in str_tags:
            obj_tags[new_tag] = (
                self.through.tag_model().objects.create(slug=new_tag, name=new_tag),
                weight
            )

        for slug, tag in obj_tags.items():
            defaults = {}
            if tag[1]:
                defaults['weight'] = tag[1]

            params = dict(tag=tag[0], defaults=defaults)
            params.update(self._lookup_kwargs())

            tagged_item, created = self.through.objects.get_or_create(**params)
            if not created and tagged_item.weight != tag[1]:
                tagged_item.weight = tag[1]
                tagged_item.save()

    @require_instance_manager
    def set(self, tags):
        self.clear()
        self.add(tags)

    @require_instance_manager
    def remove(self, tags):
        str_tags = set()
        for tag in tags:
            if isinstance(tag, (tuple, list)):
                tag = tag[0]
            if isinstance(tag, self.through.tag_model()):
                tag = tag.slug
            str_tags.add(tag)

        self.through.objects.filter(**self._lookup_kwargs()).filter(
            tag__slug__in=str_tags).delete()
