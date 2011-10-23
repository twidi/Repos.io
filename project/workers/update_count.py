#!/usr/bin/env python
"""
Update count for objects (core.models.SyncableModel.update_count)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys

from django.conf import settings
from django.utils import simplejson

import traceback
from datetime import datetime

from haystack import site
import redis

from core.models import Account, Repository

run_ok = True

def parse_json(json):
    """
    Parse the data got from redis list
    """
    # unserialize
    data = simplejson.loads(json)

    # parse object string
    model_name, id = data['object'].split(':')
    if model_name == 'core.account':
        model = Account
    elif model_name == 'core.repository':
        model = Repository
    else:
        raise Exception('Invalid object string')

    # load object
    data['object_str'] = data['object']
    data['object'] = model.objects.get(pk=id)

    return data

def main():
    """
    Main function to run forever...
    """
    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    nb = 0
    while run_ok:
        list_name, json = redis_instance.blpop(settings.WORKER_UPDATE_COUNT_KEY)

        nb += 1
        len_to_update = redis_instance.llen(settings.WORKER_UPDATE_COUNT_KEY)

        d = datetime.now()

        try:
            data = parse_json(json)
            sys.stderr.write("[%s  #%d | left : %d] %s.%s (%s)" % (d, nb, len_to_update, data['object_str'], data['count_type'], data['object']))

            data['object'].update_count(
                name = data['count_type'],
                save = True,
                use_count = data['use_count'],
                async = False
            )

        except Exception, e:
            sys.stderr.write(" => ERROR : %s (see below)\n" % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
            sys.stderr.write("====================================================================\n")

        else:
            try:
                count = getattr(data['object'], '%s_count' % data['count_type'])
            except:
                count = 'ERROR'
            sys.stderr.write(" in %s (%s)\n" % (datetime.now()-d, count))

def signal_handler(signum, frame):
    global run_ok
    run_ok = False
    sys.exit(0)

if __name__ == "__main__":
    stop_signal(signal_handler)
    main()
