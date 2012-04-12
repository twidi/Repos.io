# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from operator import itemgetter

from django_globals import globals
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import HttpResponseBadRequest

from notes.models import Note

from private.forms import (NoteForm, NoteDeleteForm,
        TagsForm, TagsDeleteForm, TagsAddOneForm, TagsRemoveOneForm, TagsCreateOneForm, TagsToggleForm)
from utils.model_utils import get_app_and_model
from core.models import get_object_from_str
from utils.djson.response import JSONResponse
from utils.views import ajax_login_required
from tagging.models import Tag
from tagging.flags import split_tags_and_flags

def get_user_note_for_object(obj, user=None):
    """
    Return a note by the current logged user for the given object
    A user can only have one note by object
    """
    user = user or globals.user
    if not (user and user.is_authenticated()):
        return None

    app_label, model_name = get_app_and_model(obj)

    try:
        return Note.objects.filter(
            author=user,
            content_type__app_label = app_label,
            content_type__model = model_name,
            object_id=obj.id
        )[0]
    except:
        return None

def return_from_editor(request, obj):
    """
    Manage redirect when we came from the editor.
    If the user clicked a button named "submit-close", he wants to
    quit the editor after action done, so redirect to the `when_finished`
    url, else use the `edit_url`.
    If not from the editor, redirect to the object default page.
    """
    if request.is_ajax():
        context = dict(
            obj_type = get_app_and_model(obj)[1],
            object = obj,
            edit_extra = obj.simple_str(),
            want_close = bool(request.POST.get('submit-close')),
        )
        return render(request, 'private/edit_private_ajax.html', context)

    param_name = 'edit_url'
    if request.POST.get('submit-close'):
        param_name = 'when_finished'
    return redirect(request.POST.get(param_name) or obj)

def ajax_edit(request, object_key):
    """
    Render the edit form, without other html, for use in ajax
    """
    return render(request, 'private/edit_private_ajax.html', dict(edit_extra = object_key))

def ajax_close(request, object_key):
    """
    Render the html to replace existing when closing via ajax the private editor
    """
    obj = get_object_from_str(object_key)
    return render(request, 'private/edit_private_ajax_onclose.html', dict(
        obj_type = get_app_and_model(obj)[1],
        object = obj,
    ))


@require_POST
@ajax_login_required
@login_required
def note_save(request):
    """
    Save a note for the current user
    """
    if ('delete' in request.POST
            or not request.POST.get('content', '').strip()):
        return note_delete(request)

    result = {}
    message_func = messages.success
    message_type = 'message'

    form = NoteForm(request.POST)
    if form.is_valid():
        note = form.save()
        noted_object = note.content_object
        message = 'Your private note was saved for `%s`'
        if request.is_ajax():
            #result['note'] = note.content
            result['note_rendered'] = note.rendered_content
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseBadRequest('Vilain :)')
        message = 'We were unable to save your note for `%s` !'
        message_func = messages.error
        message_type = 'error'

    message = message % noted_object

    if request.is_ajax():
        result[message_type] = message
        return JSONResponse(result)
    else:
        message_func(request, message)
        return redirect(noted_object or '/')


@require_POST
@ajax_login_required
@login_required
def note_delete(request):
    """
    Delete a note for the current user
    """

    result = {}
    message_func = messages.success
    message_type = 'message'

    form = NoteDeleteForm(request.POST)
    if form.is_valid():
        noted_object = form.get_related_object()
        form.save()
        message = 'Your private note for `%s` was deleted'
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseBadRequest('Vilain :)')
        message = 'We were unable to delete your note for `%s`!'
        message_func = messages.error
        message_type = 'error'

    message = message % noted_object

    if request.is_ajax():
        result[message_type] = message
        return JSONResponse(result)
    else:
        message_func(request, message)
        return redirect(noted_object or '/')


def get_user_tags_for_object(obj, user=None):
    """
    Return all tags associated to an object by the current logged user
    """
    user = user or globals.user
    if not (user and user.is_authenticated()):
        return None

    return obj.all_private_tags(user)


@require_POST
@ajax_login_required
@login_required
def tags_save(request):
    """
    Save some tags for the current user
    """
    view_data = dict(
        save = dict(
            form = TagsForm,
            success = 'Your private tags were saved',
            error = 'We were unable to save your tags !',
        ),
        add = dict(
            form = TagsAddOneForm,
            success = 'Your private tags was added',
            error = 'We were unable to add your tag !',
        ),
        remove = dict(
            form = TagsRemoveOneForm,
            success = 'Your private tags was removed',
            error = 'We were unable to remove your tag !',
        ),
        create = dict(
            form = TagsCreateOneForm,
            success = 'Your private tags was added',
            error = 'We were unable to add your tag ! (you must provide one...)',
        ),
    )

    action = request.POST.get('act', 'save')

    form = view_data[action]['form'](request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, view_data[action]['success'])
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, view_data[action]['error'])

    return return_from_editor(request, tagged_object)


@require_POST
@ajax_login_required
@login_required
def tags_delete(request):
    """
    Delete some tags for the current user
    """
    form = TagsDeleteForm(request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, 'Your private tags were deleted')
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, 'We were unable to delete your tags !')

    return return_from_editor(request, tagged_object)

## BELOW : new front ##

def _get_all_tags(request, model):
    return split_tags_and_flags(Tag.objects.filter(
                **{'private_%s_tags__owner' % model: request.user}).distinct(), model)

def get_user_tags(request):
    """
    Return the tags to be used in the search form filter.
    Work is done to note if tags are only for repositories, only for people
    or both.
    """
    # TODO => cache !

    if hasattr(request, '_all_user_tags'):
        return request._all_user_tags

    result = {'has': {}, 'for_only': {}}
    if request.user.is_authenticated():
        tags = {}
        types = ('places', 'projects', 'tags')
        for model in ('account', 'repository'):
            tags[model] = _get_all_tags(request, model)
            for tag_type in types:
                tags[model][tag_type] = set(tags[model][tag_type])

        ta, tr = tags['account'], tags['repository']
        for tag_type in types:
            set_a, set_r = ta[tag_type], tr[tag_type]
            result['has'][tag_type] = True
            if not set_a and not set_r:
                result['has'][tag_type] = False
            elif not set_a:
                result['for_only'][tag_type] = 'repositories'
            elif not set_r:
                result['for_only'][tag_type] = 'people'
            else:
                for tag in set_r - set_a:
                    tag.for_only = 'repositories'
                for tag in set_a - set_r:
                    tag.for_only = 'people'
            tags[tag_type] = set_a.union(set_r)

        for tag_type in types:
            result[tag_type] = []
            for tag in tags[tag_type]:
                tag_dict = dict(
                    slug=tag.slug,
                    name=tag.name,
                )
                for_only = getattr(tag, 'for_only', None)
                if for_only is not None:
                    tag_dict['for_only'] = for_only
                result[tag_type].append(tag_dict)


            result[tag_type] = sorted(result[tag_type], key=itemgetter('name'))

    request._all_user_tags = result
    return result

TOGGLABLE = {
    'star': {
        'tag': 'starred',
        'title_on': 'Starred',
        'title_off': 'Star it',
    },
    'check-later': {
        'tag': 'check later',
        'title_on': 'You want to check it later',
        'title_off': 'Click to check it later',
    },
}

@require_POST
@ajax_login_required
@login_required
def toggle(request, key, template=None):

    post = dict(tag = TOGGLABLE[key]['tag'])

    for var in ('content_type', 'object_id'):
        if var in request.POST:
            post[var] = request.POST[var]

    form = TagsToggleForm(post)

    if form.is_valid():
        tagged_object = form.get_related_object()
        is_set = form.save()
        flag = post['tag']
        message = 'Your `%s` flag was %s' % (flag, 'set' if is_set else 'removed')
        if request.is_ajax():
            return JSONResponse(dict(
                flag = flag,
                is_set = is_set,
                title = TOGGLABLE[key]['title_on' if is_set else 'title_off'],
                message = message,
            ))
        else:
            messages.success(request, message)
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        message = 'We were unable to toggle your flag'
        if request.is_ajax():
            return JSONResponse(dict(error=message))
        else:
            messages.error(request, message)

    return redirect(tagged_object)

def _get_tag_type(tag):
    try:
        tag_type = tag[0]
        return 'place' if tag_type == '@' else 'project' if tag_type == '#' else 'tag'
    except:
        return tag

@require_POST
@ajax_login_required
@login_required
def tag_save(request):

    view_data = dict(
        #save = dict(
        #    form = TagsForm,
        #    success = 'Your private tags were saved',
        #    error = 'We were unable to save your tags !',
        #),
        add = dict(
            form = TagsAddOneForm,
            success = 'Your private %s for `%s` was just added',
            error = 'We were unable to add your private %s for `%s` !',
            data = dict(is_set=True),
        ),
        remove = dict(
            form = TagsRemoveOneForm,
            success = 'Your private %s for `%s` was just removed',
            error = 'We were unable to remove your private %s for `%s` !',
            data = dict(is_set=False),
        ),
        create = dict(
            form = TagsCreateOneForm,
            success = 'Your private %s for `%s` was just added',
            error = 'We were unable to add your private %s for `%s` ! (you must provide one...)',
            data = dict(is_set=True),
        ),
    )

    action = request.POST.get('act', 'create')

    form = view_data[action]['form'](request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        tag_name = form.cleaned_data['tag'][0]
        message = view_data[action]['success'] % (
            _get_tag_type(tag_name),
            tagged_object,
        )
        if request.is_ajax():
            result = dict(
                view_data[action]['data'],
                message = message,
            )
            if action == 'create':
                result['slug'] = Tag.objects.filter(**{
                    'private_%s_tags__owner' % tagged_object.model_name: globals.user,
                    'name': tag_name
                }).values_list('slug', flat=True)[0]
            return JSONResponse(result)
        messages.success(request, message)
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        message = view_data[action]['error'] % (
            _get_tag_type(request.POST.get('tag', '')),
            tagged_object,
        )
        if request.is_ajax():
            return JSONResponse(dict(error=message))
        else:
            messages.error(request, message)

    return redirect(tagged_object.get_edit_tags_url() or '/')
