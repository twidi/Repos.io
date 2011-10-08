from django.db.models.sql.query import get_proxied_model

from haystack.models import SearchResult

def get_app_and_model(instance):
    """
    Return the app_label and model_name for the given instance.
    Work for normal model instance but also a proxied one (think `only` and
    `defer`), and even for instance of SearchResult (haystack)
    """
    if isinstance(instance, SearchResult):
        app_label, model_name = instance.app_label, instance.model_name
    else:
        meta = instance._meta
        if getattr(instance, '_deferred', False):
            meta = get_proxied_model(meta)._meta
        app_label, model_name = meta.app_label, meta.module_name

    return app_label, model_name
