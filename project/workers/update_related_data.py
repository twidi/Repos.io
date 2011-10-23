#!/usr/bin/env python
"""
Update related data (score, haystack, tags) for objects (core.models.SyncableModel.update_related_data)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys
import traceback
from datetime import datetime

from django.conf import settings

from haystack import site
import redis
from redisco.containers import Set

from core.models import Account, Repository

run_ok = True

def main():
    """
    Main function to run forever...
    """
    redis_instance = redis.Redis(**settings.REDIS_PARAMS)
    to_update_set = Set(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY)

    nb = 0
    while True:
        list_name, obj_str = redis_instance.blpop(settings.WORKER_UPDATE_RELATED_DATA_KEY)
        try:
            to_update_set.remove(obj_str)
        except:
            pass

        nb += 1
        len_to_update = len(to_update_set)

        d = datetime.now()
        sys.stderr.write("[%s  #%d | left : %d] %s" % (d, nb, len_to_update, obj_str))

        try:
            # find the object

            model_name, id = obj_str.split(':')
            select_related = ()
            if model_name == 'core.account':
                model = Account
            elif model_name == 'core.repository':
                model = Repository
                select_related = ('owner',)
            else:
                raise Exception('Invalid object string')

            obj = model.objects
            if select_related:
                obj = obj.select_related(*select_related)
            obj = obj.get(pk=id)

            sys.stderr.write(' (%s)' % obj)

            # if still here, update the object
            obj.update_related_data(async=False)

        except Exception, e:
            sys.stderr.write(" => ERROR : %s (see below)\n" % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
            sys.stderr.write("====================================================================\n")

        else:
            sys.stderr.write(" in %s =>  score=%d, tags=(%s)\n" % (datetime.now()-d, obj.score, ', '.join(obj.all_public_tags().values_list('slug', flat=True))))

def signal_handler(signum, frame):
    global run_ok
    run_ok = False
    sys.exit(0)

if __name__ == "__main__":
    stop_signal(signal_handler)
    main()
