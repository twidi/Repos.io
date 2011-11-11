from core.core_utils import slugify

FLAGS = ('starred', 'used', 'check later')

def split_tags_and_flags(tags, tags_are_dict=False):
    """
    Based on the given list of flags, we return a dict with 3 list of flags :
    - one with flags used
    - one with flags not used
    - one with the other tags
    """
    final_tags = []
    special_tags = list(FLAGS)
    used_special_tags = []
    for tag in tags:
        if tags_are_dict:
            lower_tag = tag['name'].lower()
        else:
            lower_tag = tag.name.lower()
        if lower_tag in FLAGS:
            used_special_tags.append(tag)
            special_tags.remove(lower_tag)
        else:
            final_tags.append(tag)

    special_tags = [dict(slug=slugify(tag), name=tag) for tag in special_tags]

    return dict(
        special = special_tags,
        special_used = used_special_tags,
        normal = final_tags
    )

