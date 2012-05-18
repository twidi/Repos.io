#!/usr/bin/env python

# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

"""
Update related data (score, haystack, tags) for objects (core.models.SyncableModel.update_related_data)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys
import traceback
from datetime import datetime

from django.conf import settings
from django.db import transaction, IntegrityError, DatabaseError

from haystack import site
import redis

from core.models import Account, Repository

run_ok = True

@transaction.commit_manually
def run_one(obj):
    """
    Update related for `obj`, in its own transaction
    """
    try:
        obj.update_related_data(async=False)
    except (IntegrityError, DatabaseError), e:
        transaction.rollback()
        raise e
    else:
        transaction.commit()

def main():
    """
    Main function to run forever...
    """
    global run_ok

    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    models = {
        'core.account': (Account, ()),
        'core.repository': (Repository, ('owner',)),
    }

    nb = 0
    max_nb = 2500
    while run_ok:
        list_name, obj_str = redis_instance.blpop(settings.WORKER_UPDATE_RELATED_DATA_KEY)
        redis_instance.srem(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY, obj_str)

        nb += 1
        len_to_update = redis_instance.scard(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY)

        d = datetime.utcnow()
        sys.stderr.write("[%s  #%d | left : %d] %s" % (d, nb, len_to_update, obj_str))

        try:
            # find the object

            model_name, id = obj_str.split(':')
            model, select_related = models[model_name]

            obj = model.objects
            if select_related:
                obj = obj.select_related(*select_related)
            obj = obj.get(pk=id)

            sys.stderr.write(' (%s)' % obj)

            # if still here, update the object
            run_one(obj)

        except Exception, e:
            sys.stderr.write(" => ERROR : %s (see below)\n" % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
            sys.stderr.write("====================================================================\n")

        else:
            sys.stderr.write(" in %s =>  score=%d, tags=(%s)\n" % (datetime.utcnow()-d, obj.score, ', '.join(obj.all_public_tags().values_list('slug', flat=True))))

        if nb >= max_nb:
            run_ok = False

def signal_handler(signum, frame):
    global run_ok
    run_ok = False

if __name__ == "__main__":
    stop_signal(signal_handler)
    main()
