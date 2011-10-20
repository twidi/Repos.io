#!/usr/bin/env python
"""
Full fetch of objects (core.models.SyncableModel.fetch_full)
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
import re

from haystack import site
import redis
from redisco.containers import List

from core.models import Account, Repository
from core.tokens import AccessTokenManager

RE_IGNORE_IMPORT = re.compile(r'(?:, )?"to_ignore": \[[^\]]*\]')

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
    lists = [settings.WORKER_FETCH_FULL_KEY % depth for depth in range(settings.WORKER_FETCH_FULL_MAX_DEPTH, -1, -1)]
    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    nb = 0
    while True:

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
            break;

        else:
            # we're good
            data['object'].fetch_full(
                token = data['token'],
                depth = data['depth'],
                to_ignore = data['to_ignore'],
                async = False
            )


if __name__ == "__main__":
    main()
