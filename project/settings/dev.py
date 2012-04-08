# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

#Settings used for development

DEBUG = True
HAYSTACK_SOLR_URL = 'http://localhost:8080/solr'

if True: #False:
    # django debug toolbar
    INSTALLED_APPS = list(INSTALLED_APPS) + [
        'debug_toolbar',
    ]
    MIDDLEWARE_CLASSES = [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ] + list(MIDDLEWARE_CLASSES)
    INTERNAL_IPS = ('127.0.0.1',)

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }

