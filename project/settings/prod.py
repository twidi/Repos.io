DEBUG = False
TEMPLATE_DEBUG = False

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        ('template_preprocessor.template.loaders.PreprocessedLoader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    )),
)

