import os.path, sys
PROJECT_PATH = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', 'EN'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.normpath(os.path.join(PROJECT_PATH, 'media/'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.normpath(os.path.join(PROJECT_PATH, 'static'))

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath(os.path.join(PROJECT_PATH, 'project_static')),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(w8x(uxj%opf^2ytd3wx_ztqu4c=7nn9yj0*6$et8z18b^(@&e'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

# django-template-preprocessor
TEMPLATE_LOADERS = (
    ('template_preprocessor.template.loaders.PreprocessedLoader',
        TEMPLATE_LOADERS
    ),
)
MEDIA_CACHE_DIR = os.path.normpath(os.path.join(MEDIA_ROOT, 'cache/'))
MEDIA_CACHE_URL = os.path.normpath(os.path.join(MEDIA_URL, 'cache/'))
TEMPLATE_CACHE_DIR = os.path.normpath(os.path.join(PROJECT_PATH, 'templates-cache/'))
# Enabled modules of the template preprocessor
TEMPLATE_PREPROCESSOR_OPTIONS = {
        # Default settings
        '*': ('html', 'whitespace-compression', ),

        # Override for specific applications
        ('django.contrib.admin', 'django.contrib.admindocs', 'debug_toolbar'): ('no-html',),
}



MIDDLEWARE_CLASSES = (
    'johnny.middleware.LocalStoreClearMiddleware',
    'johnny.middleware.QueryCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_globals.middleware.Global',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'project.context_processors.design',
    'project.context_processors.caching',
    'project.core.context_processors.backends',
    'project.core.context_processors.objects',
)

ROOT_URLCONF = 'project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath(os.path.join(PROJECT_PATH, 'templates')),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.markup',

    # apps
    'django_extensions',
    'social_auth',
    'django_globals',
    'haystack',
    'saved_searches',
    'pure_pagination',
    'notes',
    'taggit',
    'template_preprocessor',

    # ours
    'utils',
    'core',
    'accounts',
    'search',
    'private',
    'tagging',
    'dashboard',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# social_autho
AUTHENTICATION_BACKENDS = (
    'social_auth.backends.contrib.github.GithubBackend',
    'django.contrib.auth.backends.ModelBackend',
)
SOCIAL_AUTH_ENABLED_BACKENDS = ('github',)
SOCIAL_AUTH_EXTRA_DATA = True
GITHUB_EXTRA_DATA = [
    ('html_url', 'home'),
    ('login', 'original_login'),
    ('avatar_url', 'avatar_url'),
]
GITHUB_AUTH_EXTRA_ARGUMENTS = {'scope': 'user,public_repo'}
SOCIAL_AUTH_ASSOCIATE_BY_MAIL = True
SOCIAL_AUTH_ERROR_KEY = 'social_errors'

LOGIN_REDIRECT_URL = '/accounts/manage/'
LOGIN_URL = '/accounts/login/'
LOGIN_ERROR_URL = '/accounts/login/'

# enabled site backends
CORE_ENABLED_BACKENDS = ('github', )

# haystack
HAYSTACK_SITECONF = 'project.search_sites'
HAYSTACK_SEARCH_ENGINE = 'solr'
# solr
HAYSTACK_SOLR_URL = 'http://url/to/solr'

# notes
NOTES_ALLOWED_MODELS = ('core.account', 'core.repository',)

# johnny-cache
CACHES = {
    'default' : dict(
        BACKEND = 'johnny.backends.memcached.PyLibMCCache',
        LOCATION = ['127.0.0.1:11211'],
        JOHNNY_CACHE = True,
    )
}
JOHNNY_MIDDLEWARE_KEY_PREFIX='jc_reposio'

# asynchronous
WORKER_FETCH_FULL_KEY = 'fetch_full:%d'

WORKER_UPDATE_RELATED_DATA_KEY = 'update_related_data'
WORKER_UPDATE_RELATED_DATA_SET_KEY = 'update_related_data_set'

# metasettings
try:
    import metasettings
    METASETTINGS_DIR    = os.path.normpath(os.path.join(PROJECT_PATH, 'settings'))
    try:
        from settings_rules import method, rules
    except ImportError, e:
        raise e
    else:
        METASETTINGS_PATTERNS = rules
        METASETTINGS_METHOD = getattr(metasettings, method)
        metasettings.init(globals())
except Exception, e:
    sys.stderr.write("Error while loading metasettings : %s\n" % e )
    try:
        from local_settings import *
    except ImportError, e:
        sys.stderr.write("Error: You should define your own settings, see settings_rules.py.sample (or just add a local_settings.py)\nError was : %s\n" % e)
        sys.exit(1)
