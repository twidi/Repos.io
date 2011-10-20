#!/usr/bin/env python
"""
Update count for objects (core.models.SyncableModel.update_count)
"""

import sys, os

# init settings path

BASE_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PROJECT_PATH = os.path.normpath(os.path.join(BASE_PATH, 'oms_project'))
sys.path[0:0] = [BASE_PATH, PROJECT_PATH]

# init django
from django.core.management import setup_environ
import settings
setup_environ(settings)
from django.conf import settings
from django.utils import simplejson

import traceback
from datetime import datetime

from haystack import site
import redis

from core.models import Account, Repository

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
    while True:
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


if __name__ == "__main__":
    main()


