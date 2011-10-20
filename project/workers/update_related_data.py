#!/usr/bin/env python
"""
Update related data (score, haystack, tags) for objects (core.models.SyncableModel.update_related_data)
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

import traceback
from datetime import datetime

from haystack import site
import redis
from redisco.containers import Set

from core.models import Account, Repository

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


if __name__ == "__main__":
    main()


