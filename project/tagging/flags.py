# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from core.core_utils import slugify

FLAGS = dict(
    account = ('starred', 'known', 'check later'),
    repository = ('starred', 'used', 'check later')
)

def split_tags_and_flags(tags, obj_type, tags_are_dict=False):
    """
    Based on the given list of flags, we return a dict with 3 list of flags :
    - one with flags used
    - one with flags not used
    - one with the other tags
    """
    final_tags = []
    special_tags = list(FLAGS[obj_type])
    used_special_tags = {}
    for tag in tags:
        if tags_are_dict:
            lower_tag = tag['name'].lower()
        else:
            lower_tag = tag.name.lower()
        if lower_tag in FLAGS[obj_type]:
            used_special_tags[lower_tag] = tag
            special_tags.remove(lower_tag)
        else:
            final_tags.append(tag)

    special_tags = [dict(slug=slugify(tag), name=tag) for tag in special_tags]

    sorted_used_special_tags = [used_special_tags[tag] for tag in FLAGS[obj_type] if tag in used_special_tags]

    return dict(
        special = special_tags,
        special_used = sorted_used_special_tags,
        normal = final_tags
    )

