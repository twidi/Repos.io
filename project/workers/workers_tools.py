# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import signal, sys, os

def init_django():
    PROJECT_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    sys.path[0:0] = [PROJECT_PATH,]
    from django.core.management import setup_environ
    import settings
    setup_environ(settings)

def stop_signal(handler):
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
