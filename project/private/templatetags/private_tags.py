from django import template
from django.core.urlresolvers import reverse

from django_globals import globals
from notes.models import Note

from private.models import ALLOWED_MODELS
from private.forms import NoteForm, NoteDeleteForm, TagsDeleteForm, TagsBaseForm
from core.models import Account, Repository
from utils.model_utils import get_app_and_model
from utils.views import get_request_param
from tagging.models import Tag
from tagging.flags import split_tags_and_flags

register = template.Library()

@register.simple_tag
def prepare_private(objects, ignore=None):
    """
    Update each object included in the `objects` with private informations (note and tags)
    All objects must be from the same content_type
    `ignore` is a string where we will search for "-tags", "-notes" and "related" to avoid compute them
    if found
    """
    try:
        if not (globals.user and globals.user.is_authenticated()):
            return ''

        # find objects' type
        obj = objects[0]

        app_label, model_name = get_app_and_model(obj)

        if '%s.%s' % (app_label, model_name) not in ALLOWED_MODELS:
            return ''

        user = globals.user

        dict_objects = dict((int(obj.pk), obj) for obj in objects)
        ids = sorted(dict_objects.keys())
        if not ids:
            return ''

        # read and save notes
        if not (ignore and '-notes' in ignore):
            notes = Note.objects.filter(
                    content_type__app_label = app_label,
                    content_type__model = model_name,
                    author = user,
                    object_id__in=ids
                    ).values_list('object_id', 'rendered_content', 'modified')

            for obj_id, note, modified in notes:
                dict_objects[obj_id].current_user_has_extra = True
                dict_objects[obj_id].current_user_has_note = True
                dict_objects[obj_id].current_user_rendered_note = note
                dict_objects[obj_id].current_user_note_modified = modified

        # read and save tags
        if not (ignore and '-tags' in ignore):
            if model_name == 'account':
                qs_tags = user.tagging_privatetaggedaccount_items
            else:
                qs_tags = user.tagging_privatetaggedrepository_items

            private_tagged_items = qs_tags.filter(
                    content_object__in=ids
                ).values_list('content_object', 'tag__name', 'tag__slug')

            for obj_id, tag, slug in private_tagged_items:
                if not getattr(dict_objects[obj_id], 'current_user_has_tags', None):
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_has_tags = True
                    dict_objects[obj_id].current_user_tags = []
                dict_objects[obj_id].current_user_tags.append(dict(name=tag, slug=slug))

            for obj in dict_objects.values():
                obj.current_user_tags = split_tags_and_flags(obj.current_user_tags, tags_are_dict=True)


        if not (ignore and '-related' in ignore):
            if model_name == 'account':
                # self
                self_accounts = Account.objects.filter(id__in=ids, user=user).values_list('id', flat=True)
                for obj_id in self_accounts:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_is_self = True

                # follows
                following = Account.objects.filter(id__in=ids, followers__user=user).values_list('id', flat=True)
                for obj_id in following:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_follows = True

                # is followed
                followed = Account.objects.filter(id__in=ids, following__user=user).values_list('id', flat=True)
                for obj_id in followed:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_followed = True

            else:
                # owns or follows
                following = Repository.objects.filter(id__in=ids, followers__user=user).values_list('id', 'owner__user_id')
                for obj_id, owner_id in following:
                    dict_objects[obj_id].current_user_has_extra = True
                    if owner_id == user.id:
                        dict_objects[obj_id].current_user_owns = True
                    else:
                        dict_objects[obj_id].current_user_follows = True

                # fork
                forked = Repository.objects.filter(id__in=ids, forks__owner__user=user).values_list('id', flat=True)
                for obj_id in forked:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_has_fork = True

        return ''
    except:
        return ''


@register.inclusion_tag('private/edit_private.html')
def edit_private(object_str):
    """
    Display the the private editor for the given object. `object_str` is the object
    representaiton as defined by the `simple_str` method in the core module.
    """
    if not (object_str and globals.user and globals.user.is_authenticated()):
        return {}

    model_name, id = object_str.split(':')
    if '.' in model_name:
        model_name = model_name.split('.')[-1]

    if model_name == 'account':
        model = Account
        model_name_plural = 'accounts'
    else:
        model = Repository
        model_name_plural = 'repositories'

    try:
        edit_object = model.objects.get(id=id)

        # get private data
        note = edit_object.get_user_note()
        private_tags = edit_object.get_user_tags()

        # get other private tags
        other_tags = Tag.objects.filter(
                **{'private_%s_tags__owner' % model_name:globals.user})
        if private_tags:
            other_tags = other_tags.exclude(
                    id__in=[t.id for t in private_tags])
        other_tags = other_tags.distinct()

        # for tags url
        if model_name == 'account':
            model_name_plural = 'accounts'
        else:
            model_name_plural = 'repositories'

        # special tags
        flags_and_tags = split_tags_and_flags(private_tags)

        return dict(
            edit_object = edit_object,
            note_save_form = NoteForm(instance=note) if note else NoteForm(noted_object=edit_object),
            note_delete_form = NoteDeleteForm(instance=note) if note else None,
            tag_save_form = TagsBaseForm(tagged_object=edit_object),
            tags_delete_form = TagsDeleteForm(tagged_object=edit_object) if private_tags else None,
            private_tags = flags_and_tags['normal'],
            other_tags = other_tags,
            special_tags = flags_and_tags['special'],
            used_special_tags = flags_and_tags['special_used'],
            url_tags = reverse('dashboard_tags', kwargs=dict(obj_type=model_name_plural)),
            edit_url = get_request_param(globals.request, 'edit_url', globals.request.get_full_path()),
            when_finished = get_request_param(globals.request, 'when_finished'),
        )

    except:
        return {}
