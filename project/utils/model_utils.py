# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

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


# BELOW : https://github.com/andymccurdy/django-tips-and-tricks/blob/master/model_update.py

import operator

from django.db.models.expressions import F, ExpressionNode

EXPRESSION_NODE_CALLBACKS = {
    ExpressionNode.ADD: operator.add,
    ExpressionNode.SUB: operator.sub,
    ExpressionNode.MUL: operator.mul,
    ExpressionNode.DIV: operator.div,
    ExpressionNode.MOD: operator.mod,
    ExpressionNode.AND: operator.and_,
    ExpressionNode.OR: operator.or_,
    }

class CannotResolve(Exception):
    pass

def _resolve(instance, node):
    if isinstance(node, F):
        return getattr(instance, node.name)
    elif isinstance(node, ExpressionNode):
        return _resolve(instance, node)
    return node

def resolve_expression_node(instance, node):
    op = EXPRESSION_NODE_CALLBACKS.get(node.connector, None)
    if not op:
        raise CannotResolve
    runner = _resolve(instance, node.children[0])
    for n in node.children[1:]:
        runner = op(runner, _resolve(instance, n))
    return runner

def update(instance, **kwargs):
    "Atomically update instance, setting field/value pairs from kwargs"
    # fields that use auto_now=True should be updated corrected, too!
    for field in instance._meta.fields:
        if hasattr(field, 'auto_now') and field.auto_now and field.name not in kwargs:
            kwargs[field.name] = field.pre_save(instance, False)

    rows_affected = instance.__class__._default_manager.filter(pk=instance.pk).update(**kwargs)

    # apply the updated args to the instance to mimic the change
    # note that these might slightly differ from the true database values
    # as the DB could have been updated by another thread. callers should
    # retrieve a new copy of the object if up-to-date values are required
    for k,v in kwargs.iteritems():
        if isinstance(v, ExpressionNode):
            v = resolve_expression_node(instance, v)
        setattr(instance, k, v)

    # If you use an ORM cache, make sure to invalidate the instance!
    #cache.set(djangocache.get_cache_key(instance=instance), None, 5)
    return rows_affected

