# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import template
register = template.Library()

@register.filter
def distinctify(objects, fields=None):
    """
    Return a distinct list (by id) of objects, but keep specific fields
    For example, with the followers of a user, we have a list of Accounts,
    each with an extra field "current_user_account_id" to save which account
    of the current user is followed.
    If an account follow more than one of the user's accouts, it will be
    present more than one time in the list.
    This function keeps only one entry of each, but regroups some fields into
    lists, so all the "current_user_account_id" of the many occurences of one
    account are stored in a "current_user_account_id_list" of the only
    occurence which this function kept.
    `fields` is a string with name of fields to regroup, separated by a coma
    (no spaces !)
    Usage : {{ mylist|distinctify:"field1,field2" }}
    """
    if not objects:
        return []

    special_fields = []
    if fields:
        special_fields = fields.split(',')

    # first test length: it's same, no need to distintify
    ids = set([obj.id for obj in objects])
    if len(ids) == len(objects):
        # check if all fields are present
        ok = True
        for field in special_fields:
            if not hasattr(objects[0], '%s_list' % field):
                ok = False
                break
        # not fields present, quickly create them
        if not ok:
            for obj in objects:
                for field in special_fields:
                    setattr(obj, '%s_list' % field, set((getattr(obj, field),)))
        return objects

    # we really have to distinct !
    result = []
    found = {}

    for obj in objects:

        if obj.id not in found:
            found[obj.id] = obj
            result.append(obj)

            for field in special_fields:
                if not hasattr(obj, '%s_list' % field):
                    setattr(obj, '%s_list' % field, set())

        for field in special_fields:
            if hasattr(obj, field):
                getattr(found[obj.id], '%s_list' % field).add(getattr(obj, field))

    return result


