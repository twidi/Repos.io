#!/usr/bin/env python
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
from redisco.containers import List

from django.conf import settings
from django.utils import simplejson

from core.models import Account, Repository
from core.tokens import AccessTokenManager

RE_IGNORE_IMPORT = re.compile(r'(?:, )?"to_ignore": \[[^\]]*\]')

current_token = None
run_ok = True

def parse_json(json):
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

    # load object
    result['object'] = model.objects.get(pk=id)

    # find a good token
    token_manager = AccessTokenManager.get_for_backend(result['object'].backend)
    result['token'] = token_manager.get_by_uid(data.get('token', None))

    # which depth...
    result['depth'] = data.get('depth', 0) or 0

    # and objects to ignore...
    result['to_ignore'] = set(data.get('to_ignore', []))

    return result

def main():
    """
    Main function to run forever...
    """
    global current_token, run_ok

    lists = [settings.WORKER_FETCH_FULL_KEY % depth for depth in range(settings.WORKER_FETCH_FULL_MAX_DEPTH, -1, -1)]
    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    nb = 0
    max_nb = 500
    while run_ok:

        # wait for new data
        list_name, json = redis_instance.blpop(lists)

        nb += 1
        len_list = redis_instance.llen(list_name)

        sys.stderr.write("\n[%s  #%d | left(%s) : %d] %s\n" % (datetime.now(), nb, list_name, len_list, RE_IGNORE_IMPORT.sub('', json)))

        try:
            # unserialize
            data = parse_json(json)
            if not data:
                raise Exception('Invalid data : %s' % data)
        except:
            sys.stderr.write("\n".join(traceback.format_exception(*sys.exc_info())))

            List(settings.WORKER_FETCH_FULL_ERROR_KEY).append(json)

        else:
            current_token = data['token']

            # we're good
            data['object'].fetch_full(
                token = data['token'],
                depth = data['depth'],
                to_ignore = data['to_ignore'],
                async = False
            )

        if nb >= max_nb:
            run_ok = False


def signal_handler(signum, frame):
    global current_token, run_ok
    if current_token:
        current_token.release()
    run_ok = False
    sys.exit(0)


if __name__ == "__main__":
    stop_signal(signal_handler)
    main()
