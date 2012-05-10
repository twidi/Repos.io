#!/usr/bin/env python

# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

"""
Full fetch of objects (core.models.SyncableModel.fetch_full)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys

import traceback
from datetime import datetime
import re

from haystack import site
import redis
from redisco.containers import List, Hash

from django.conf import settings
from django.utils import simplejson
from django.db import IntegrityError, DatabaseError

from core.models import Account, Repository
from core.tokens import AccessTokenManager

RE_IGNORE_IMPORT = re.compile(r'(?:, )?"to_ignore": \[[^\]]*\]')

run_ok = True

def parse_json(json, priority):
    """
    Parse the data got from redis lists
    """
    result = {}

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

    # check if object not already done or to be done in another list
    try:
        wanted_priority = int(Hash(settings.WORKER_FETCH_FULL_HASH_KEY)[data['object']])
    except:
        wanted_priority = None
    if wanted_priority is None or wanted_priority != priority:
        return { 'ignore': True }

    # load object
    result['object'] = model.objects.get(pk=id)

    # find a good token
    token_manager = AccessTokenManager.get_for_backend(result['object'].backend)
    result['token'] = token_manager.get_by_uid(data.get('token', None))

    # which depth...
    result['depth'] = data.get('depth', 0) or 0

    # maybe a user to notity
    result['notify_user'] = data.get('notify_user', None)

    return result

def main():
    """
    Main function to run forever...
    """
    global run_ok

    lists = [settings.WORKER_FETCH_FULL_KEY % priority for priority in range(settings.WORKER_FETCH_FULL_MAX_PRIORITY, -1, -1)]
    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    nb = 0
    max_nb = 500
    while run_ok:

        # wait for new data
        list_name, json = redis_instance.blpop(lists)

        priority = int(list_name[-1])

        nb += 1
        len_list = redis_instance.llen(list_name)

        sys.stderr.write("\n[%s  #%d | left(%s) : %d] %s\n" % (datetime.now(), nb, list_name, len_list, RE_IGNORE_IMPORT.sub('', json)))

        try:
            # unserialize
            data = parse_json(json, priority)
            if not data:
                raise Exception('Invalid data : %s' % data)
        except:
            sys.stderr.write("\n".join(traceback.format_exception(*sys.exc_info())))

            List(settings.WORKER_FETCH_FULL_ERROR_KEY).append(json)

        else:
            if data.get('ignore', False):
                sys.stderr.write("  => ignore\n")

            else:
                # we're good

                params = dict(
                    token = data['token'],
                    depth = data['depth'],
                    async = False
                )
                if data.get('notify_user', None):
                    params['notify_user'] = data['notify_user']

                _, error = data['object'].fetch_full(**params)

                if error and isinstance(error, (DatabaseError, IntegrityError)):
                    # stop the process if integrityerror to start a new transaction
                    run_ok = False

        if nb >= max_nb:
            run_ok = False


def signal_handler(signum, frame):
    global run_ok
    run_ok = False


if __name__ == "__main__":
    stop_signal(signal_handler)
    main()
