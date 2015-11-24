# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from lxml.html.clean import clean_html

from django import template
from django.contrib.markup.templatetags import markup
from django.utils.safestring import mark_safe
from django.template.defaultfilters import urlize
from django.db.models.sql.query import get_proxied_model

from haystack.models import SearchResult

from core.models import SyncableModel
from core.backends import BaseBackend, get_backend
from tagging.flags import split_tags_and_flags
from utils.model_utils import get_app_and_model
from adv_cache_tag.tag import CacheTag

register = template.Library()

@register.filter
def supports(backend, functionnality):
    """
    Return True if the given backend supports the given functionnality.
    `backend` can be a backend name, or a backend object
    """

    if isinstance(backend, basestring):
        backend = get_backend(backend)
        if not backend:
            return False

    if isinstance(backend, BaseBackend):
        return backend.supports(functionnality)

    return False

@register.filter
def links_with_user(obj, user):
    """
    Return informations about some links between the given object (account or repository) and the given user
    """
    try:
        return obj.links_with_user(user)
    except:
        return {}

@register.filter
def note_and_tags(obj, user):
    """
    Return the note and tags for the given object (account or repository) by the given user
    """
    try:
        note = obj.get_user_note(user)
        private_tags = obj.get_user_tags(user)
        if private_tags:
            app_label, model_name = get_app_and_model(obj)
            flags_and_tags = split_tags_and_flags(private_tags, model_name)
        else:
            flags_and_tags = None

        return dict(
            note = note,
            flags_and_tags = flags_and_tags
        )
    except:
        return {}

@register.filter
def readme(repository):
    """
    Return a rendered version of the readme for the given repository
    """
    if not repository.readme or not repository.readme.strip():
        return 'No readme :('

    readme = None

    try:
        if repository.readme_type == 'html':
            readme = repository.readme_html
        elif repository.readme_type == 'markdown':
            readme = markup.markdown(repository.readme)
        elif repository.readme_type == 'textile':
            readme = markup.textile(repository.readme)
        elif repository.readme_type == 'rest':
            readme = markup.restructuredtext(repository.readme)
    except:
        pass

    if not readme:
        readme = '<pre>%s</pre>' % urlize(repository.readme)

    try:
        result = mark_safe(clean_html(readme))
    except:
        result = 'Unreadble readme :('

    return result
readme.is_safe = True


@register.filter
def url(obj, url_type):
    """
    Return a specific url for the given object
    """
    try:
        return obj._get_url(url_type)
    except:
        return ''

@register.filter
def count_tags(obj, tags_type):
    """
    Return the number of tags of the given type for the given object
    """
    try:
        return obj.count_tags(tags_type)
    except:
        return ''

class CoreCacheTag(CacheTag):
    class Meta(CacheTag.Meta):
        include_pk = True
        compress = True
        compress_spaces = True
        versioning = True
        internal_version = '0.5'

    def create_content(self):
        obj = self.context['obj']

        current_user_data_keys = [key for key in vars(obj) if key.startswith('current_user_')]

        if not isinstance(obj, SyncableModel) or obj._deferred:

            if isinstance(obj, SearchResult):
                model = obj.model
            else:
                model = get_proxied_model(obj._meta)

            print "RENDER %s.%s" % (model, obj.pk)

            full_obj = model.for_user_list.get(id=obj.pk)
            for key in current_user_data_keys:
                setattr(full_obj, key, getattr(obj, key))
            self.context['obj'] = self.context[obj.model_name] = full_obj

        super(CoreCacheTag, self).create_content()

CoreCacheTag.register(register, 'corecache');
