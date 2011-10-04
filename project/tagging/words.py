"""
This module is here to create the firsts tags, based on thousands of
repositories : get all words, keep the most importants and save them as tags
Usage:
    all_words = {}
    repositories_to_words(Repository.objects.all(), words=all_words, return_words=False)
    all_tags = sort_words(all_words, limit=2500, return_format='set')
    add_tags(all_tags, official=True, check_duplicates=False)
"""

import string
import re


def get_ignore_words():
    """
    When needed, compute/cache and return a list of words to ignore
    """
    if get_ignore_words._ignore_cache is None:

        # stop words from postgresql files

        #import codecs
        #from core.utils import slugify
        #get_ignore_words._ignore_cache = set()
        #for filename in ('english', 'french', 'german', 'spanish',):
        #    f=codecs.open('/usr/share/postgresql/8.4/tsearch_data/%s.stop' % filename, 'r', 'utf-8')
        #    get_ignore_words._ignore_cache.update(slugify(li) for li in [l.strip() for l in f] if len(li) > 1)
        #    f.close()
        get_ignore_words._ignore_cache = set(('aber', 'about', 'above', 'after', 'again', 'against', 'ai', 'aie', 'aient', 'aies', 'ait', 'al', 'algo', 'algunas', 'algunos', 'all', 'alle', 'allem', 'allen', 'aller', 'alles', 'als', 'also', 'am', 'an', 'and', 'ander', 'andere', 'anderem', 'anderen', 'anderer', 'anderes', 'anderm', 'andern', 'anderr', 'anders', 'ante', 'antes', 'any', 'are', 'as', 'at', 'au', 'auch', 'auf', 'aura', 'aurai', 'auraient', 'aurais', 'aurait', 'auras', 'aurez', 'auriez', 'aurions', 'aurons', 'auront', 'aus', 'aux', 'avaient', 'avais', 'avait', 'avec', 'avez', 'aviez', 'avions', 'avons', 'ayant', 'ayante', 'ayantes', 'ayants', 'ayez', 'ayons', 'be', 'because', 'been', 'before', 'bei', 'being', 'below', 'between', 'bin', 'bis', 'bist', 'both', 'but', 'by', 'can', 'ce', 'ces', 'como', 'con', 'contra', 'cual', 'cuando', 'da', 'damit', 'dann', 'dans', 'das', 'dasselbe', 'dazu', 'de', 'dein', 'deine', 'deinem', 'deinen', 'deiner', 'deines', 'del', 'dem', 'demselben', 'den', 'denn', 'denselben', 'der', 'derer', 'derselbe', 'derselben', 'des', 'desde', 'desselben', 'dessen', 'dich', 'did', 'die', 'dies', 'diese', 'dieselbe', 'dieselben', 'diesem', 'diesen', 'dieser', 'dieses', 'dir', 'do', 'doch', 'does', 'doing', 'don', 'donde', 'dort', 'down', 'du', 'durante', 'durch', 'during', 'each', 'ein', 'eine', 'einem', 'einen', 'einer', 'eines', 'einig', 'einige', 'einigem', 'einigen', 'einiger', 'einiges', 'einmal', 'el', 'ella', 'ellas', 'elle', 'ellos', 'en', 'entre', 'er', 'era', 'erais', 'eramos', 'eran', 'eras', 'eres', 'es', 'esa', 'esas', 'ese', 'eso', 'esos', 'est', 'esta', 'estaba', 'estabais', 'estabamos', 'estaban', 'estabas', 'estad', 'estada', 'estadas', 'estado', 'estados', 'estais', 'estamos', 'estan', 'estando', 'estar', 'estara', 'estaran', 'estaras', 'estare', 'estareis', 'estaremos', 'estaria', 'estariais', 'estariamos', 'estarian', 'estarias', 'estas', 'este', 'esteis', 'estemos', 'esten', 'estes', 'esto', 'estos', 'estoy', 'estuve', 'estuviera', 'estuvierais', 'estuvieramos', 'estuvieran', 'estuvieras', 'estuvieron', 'estuviese', 'estuvieseis', 'estuviesemos', 'estuviesen', 'estuvieses', 'estuvimos', 'estuviste', 'estuvisteis', 'estuvo', 'et', 'etaient', 'etais', 'etait', 'etant', 'etante', 'etantes', 'etants', 'ete', 'etee', 'etees', 'etes', 'etiez', 'etions', 'etwas', 'eu', 'euch', 'eue', 'euer', 'eues', 'eumes', 'eure', 'eurem', 'euren', 'eurent', 'eurer', 'eures', 'eus', 'eusse', 'eussent', 'eusses', 'eussiez', 'eussions', 'eut', 'eutes', 'eux', 'few', 'for', 'from', 'fue', 'fuera', 'fuerais', 'fueramos', 'fueran', 'fueras', 'fueron', 'fuese', 'fueseis', 'fuesemos', 'fuesen', 'fueses', 'fui', 'fuimos', 'fuiste', 'fuisteis', 'fumes', 'fur', 'furent', 'further', 'fus', 'fusse', 'fussent', 'fusses', 'fussiez', 'fussions', 'fut', 'futes', 'gegen', 'gewesen', 'ha', 'hab', 'habe', 'habeis', 'haben', 'habia', 'habiais', 'habiamos', 'habian', 'habias', 'habida', 'habidas', 'habido', 'habidos', 'habiendo', 'habra', 'habran', 'habras', 'habre', 'habreis', 'habremos', 'habria', 'habriais', 'habriamos', 'habrian', 'habrias', 'had', 'han', 'has', 'hasta', 'hat', 'hatte', 'hatten', 'have', 'having', 'hay', 'haya', 'hayais', 'hayamos', 'hayan', 'hayas', 'he', 'hemos', 'her', 'here', 'hers', 'herself', 'hier', 'him', 'himself', 'hin', 'hinter', 'his', 'how', 'hube', 'hubiera', 'hubierais', 'hubieramos', 'hubieran', 'hubieras', 'hubieron', 'hubiese', 'hubieseis', 'hubiesemos', 'hubiesen', 'hubieses', 'hubimos', 'hubiste', 'hubisteis', 'hubo', 'ich', 'if', 'ihm', 'ihn', 'ihnen', 'ihr', 'ihre', 'ihrem', 'ihren', 'ihrer', 'ihres', 'il', 'im', 'in', 'indem', 'ins', 'into', 'is', 'ist', 'it', 'its', 'itself', 'je', 'jede', 'jedem', 'jeden', 'jeder', 'jedes', 'jene', 'jenem', 'jenen', 'jener', 'jenes', 'jetzt', 'just', 'kann', 'kein', 'keine', 'keinem', 'keinen', 'keiner', 'keines', 'konnen', 'konnte', 'la', 'las', 'le', 'les', 'leur', 'lo', 'los', 'lui', 'ma', 'machen', 'mais', 'man', 'manche', 'manchem', 'manchen', 'mancher', 'manches', 'mas', 'me', 'mein', 'meine', 'meinem', 'meinen', 'meiner', 'meines', 'meme', 'mes', 'mi', 'mia', 'mias', 'mich', 'mio', 'mios', 'mir', 'mis', 'mit', 'moi', 'mon', 'more', 'most', 'mucho', 'muchos', 'muss', 'musste', 'muy', 'my', 'myself', 'nach', 'nada', 'ne', 'ni', 'nicht', 'nichts', 'no', 'noch', 'nor', 'nos', 'nosotras', 'nosotros', 'not', 'notre', 'nous', 'now', 'nuestra', 'nuestras', 'nuestro', 'nuestros', 'nun', 'nur', 'ob', 'oder', 'of', 'off', 'ohne', 'on', 'once', 'only', 'ont', 'or', 'os', 'other', 'otra', 'otras', 'otro', 'otros', 'ou', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'par', 'para', 'pas', 'pero', 'poco', 'por', 'porque', 'pour', 'qu', 'que', 'qui', 'quien', 'quienes', 'sa', 'same', 'se', 'sea', 'seais', 'seamos', 'sean', 'seas', 'sehr', 'sein', 'seine', 'seinem', 'seinen', 'seiner', 'seines', 'selbst', 'sentid', 'sentida', 'sentidas', 'sentido', 'sentidos', 'sera', 'serai', 'seraient', 'serais', 'serait', 'seran', 'seras', 'sere', 'sereis', 'seremos', 'serez', 'seria', 'seriais', 'seriamos', 'serian', 'serias', 'seriez', 'serions', 'serons', 'seront', 'ses', 'she', 'should', 'si', 'sich', 'sie', 'siente', 'sin', 'sind', 'sintiendo', 'so', 'sobre', 'soient', 'sois', 'soit', 'solche', 'solchem', 'solchen', 'solcher', 'solches', 'soll', 'sollte', 'some', 'sommes', 'somos', 'son', 'sondern', 'sonst', 'sont', 'soy', 'soyez', 'soyons', 'su', 'such', 'suis', 'sur', 'sus', 'suya', 'suyas', 'suyo', 'suyos', 'ta', 'tambien', 'tanto', 'te', 'tendra', 'tendran', 'tendras', 'tendre', 'tendreis', 'tendremos', 'tendria', 'tendriais', 'tendriamos', 'tendrian', 'tendrias', 'tened', 'teneis', 'tenemos', 'tenga', 'tengais', 'tengamos', 'tengan', 'tengas', 'tengo', 'tenia', 'teniais', 'teniamos', 'tenian', 'tenias', 'tenida', 'tenidas', 'tenido', 'tenidos', 'teniendo', 'tes', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'ti', 'tiene', 'tienen', 'tienes', 'to', 'todo', 'todos', 'toi', 'ton', 'too', 'tu', 'tus', 'tuve', 'tuviera', 'tuvierais', 'tuvieramos', 'tuvieran', 'tuvieras', 'tuvieron', 'tuviese', 'tuvieseis', 'tuviesemos', 'tuviesen', 'tuvieses', 'tuvimos', 'tuviste', 'tuvisteis', 'tuvo', 'tuya', 'tuyas', 'tuyo', 'tuyos', 'uber', 'um', 'un', 'una', 'und', 'under', 'une', 'uno', 'unos', 'uns', 'unse', 'unsem', 'unsen', 'unser', 'unses', 'unter', 'until', 'up', 'very', 'viel', 'vom', 'von', 'vor', 'vos', 'vosostras', 'vosostros', 'votre', 'vous', 'vuestra', 'vuestras', 'vuestro', 'vuestros', 'wahrend', 'war', 'waren', 'warst', 'was', 'we', 'weg', 'weil', 'weiter', 'welche', 'welchem', 'welchen', 'welcher', 'welches', 'wenn', 'werde', 'werden', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'wie', 'wieder', 'will', 'wir', 'wird', 'wirst', 'with', 'wo', 'wollen', 'wollte', 'wurde', 'wurden', 'ya', 'yo', 'you', 'your', 'yours', 'yourself', 'yourselves', 'zu', 'zum', 'zur', 'zwar', 'zwischen'))

        # specific words to ignore
        get_ignore_words._ignore_cache.update(('http', 'https', 'www', 'com', 'net', 'org', 'de', 'versions', 'version', 'get', 'got', 'read', 'load', 'clone', 'repository', 'repositories', 'clones', 'fork', 'forks' 'forked', 'cloned', 'without', 'handle', 'manage', 'manages', 'managing', 'handles', 'make', 'makes', 'like', 'mimic', 'mimmics', 'modified', 'full', 'play', 'using', 'use', 'used', 'uses', 'work', 'works', 'worked', 'please', 'alpha', 'beta', 'info', 'infos', 'information', 'informations', 'etc', 'simple', 'yet', 'plus', 'think', 'type', 'anything', 'anyone', 'like', 'high', 'low', 'fast', 'slow', 'medium', 'half', 'based', 'cute', 'place', 'super', 'per', 'create', 'created', 'creates', 'top', 'see', 'useful', 'classic', 'set', 'party', 'second', 'first', 'third', 'pay', 'via', 'fuzzy', 'missing', 'improved', 'working', 'item', 'branch', 'items', 'branches', 'anywhere', 'little', 'big', 'one', 'two', 'three', 'many', 'more', 'long', 'short', 'pure', 'friendly', 'easy', 'hard', 'keep', 'non', 'meetup', 'send', 'sends', 'sending', 'custom', 'global', 'local', 'set', 'sets', 'list', 'lists', 'stuff', 'linked', 'link', 'links', 'line', 'lines', 'hot', 'thing', 'things', 'stage', 'staging', 'prod', 'production', 'world', 'word', 'auto', 'news', 'click', 'development', 'dev', 'devel', 'good', 'bad', 'soft', 'feature', 'features', 'object', 'objects', 'plus', 'help', 'slick', 'thin', 'thick', 'way', 'prog', 'program', 'programming', 'programs', 'love', 'real', 'util', 'utils', 'utility', 'utilities'))

    return get_ignore_words._ignore_cache
get_ignore_words._ignore_cache = None

# some synonyms
synonyms = {
    'js': 'javascript',
    'py': 'python',
    'rb': 'ruby',
    'ror': 'rails',
    'tools': 'tool',
    'plugins': 'plugin',
    'extensions': 'extension',
    'add-on': 'addon',
    'add-ons': 'addon',
    'addons': 'addon',
    'apps': 'app',
    'applications': 'app',
    'application': 'app',
    'tests': 'test',
    'testing': 'test',
    'templates': 'template',
    'dotfiles': 'dotfile',
    'files': 'file',
    'demos': 'demo',
    'examples': 'example',
    'samples': 'sample',
    'recipes': 'recipe',
    'docs': 'doc',
    'documentation': 'doc',
    'resources': 'resource',
    'sessions': 'session',
    'assets': 'asset',
    'themes': 'theme',
    'migrations': 'migration',
    'files': 'file',
    'hg': 'mercurial',
    'subversion': 'svn',
    'commons': 'common',
    'couch': 'couchdb',
    'mongo': 'mongodb',
    'pgsql': 'postresql',
    'postgre': 'postgresql',
    'postgres': 'postgresql',
    'pg': 'postgresql',
    'setting': 'settings',
    'helpers': 'helper',
    'cookbooks': 'cookbook',
    'messages': 'message',
    'modules': 'module',
    'snippets': 'snippet',
    'snip': 'snippet',
    'metric': 'metrics',
    'analytic': 'analytics',
    'services': 'service',
    'maps': 'map',
    'buttons': 'button',
    'stats': 'stat',
    'statistic': 'stat',
    'statistics': 'stat',
    'logger': 'log',
    'models': 'model',
    'basics': 'basic',
    'scripts': 'script',
    'tags': 'tag',
    'tagging': 'tag',
    'tagger': 'tag',
    'forms': 'form',
    'events': 'event',
    'tables': 'table',
    'bundles': 'bundle',
    'bundler': 'bundle',
    'validations': 'validation',
    'validate': 'validation',
    'validates': 'validation',
    'validator': 'validation',
    'notifications': 'notification',
    'favorites': 'favorite',
    'fav': 'favotire',
    'notif': 'notification',
    'cookies': 'cookie',
    'lang': 'language',
    'langs': 'lang',
    'metas': 'meta',
    'extras': 'extra',
    'thumbnails': 'thumbnail',
    'images': 'image',
    'img': 'image',
    'pygments': 'pygment',
    'views': 'view',
    'fields': 'field',
    'errors': 'error',
    'pages': 'page',
    'paginate': 'pagination',
    'formats': 'format',
    'types': 'type',
    'queues': 'queue',
    'keys': 'key',
    'values': 'value',
    'hooks': 'hook',
    'permissions': 'permission',
    'rubygems': 'gem',
    'gems': 'gem',
    'rubygem': 'gem',
    'friends': 'friend',
    'generators': 'generator',
    'ratings': 'rate',
    'rating': 'rate',
    'projects': 'project',
    'tweet': 'twitter',
    'twit': 'twitter',
    'tweets': 'twitter',
    'fb': 'facebook',
    'users': 'user',
    'members': 'member',
    'defaults': 'default',
    'mixins': 'mixin',
    'tested': 'test',
    'documented': 'doc',
    'translation': 'i18n',
    'translate': 'i18n',
    'translatable': 'i18n',
    'translator': 'i18n',
    'translations': 'i18n',
    'languages': 'i18n',
    'multilingual': 'i18n',
    'contents': 'content',
    'issues': 'issue',
    'mailer': 'mail',
    'mails': 'mail',
    'email': 'mail',
    'emails': 'mail',
    'questions': 'question',
    'authentication': 'auth',
    'authorization': 'auth',
    'sites': 'site',
    'streams': 'stream',
    'follower': 'follow',
    'following': 'follow',
    'followers': 'follow',
    'followings': 'follow',
    'cached': 'cache',
    'caching': 'cache',
    'blocks': 'block',
    'wrapper': 'wrap',
    'wrapping': 'wrap',
    'programs': 'program',
    'methods': 'method',
    'pal': 'paypal',
    'log': 'logging',
    'logs': 'logging',
    'widgets': 'widget',
    'comments': 'comment',
    'voting': 'vote',
    'databases': 'database',
    'db': 'database',
    'dbs': 'database',
    'sgbd': 'database',
    'actor': 'actors',
    'generating': 'generate',
    'actions': 'action',
    'collections': 'collection',
    'boxes': 'box',
    'extended': 'extend',
    'extends': 'extend',
    'extending': 'extend',
    'requests': 'request',
    'documents': 'document',
    'hosts': 'host',
    'commands': 'command',
    'tip': 'tips and tricks',
    'tips': 'tips and tricks',
    'trick': 'tips and tricks',
    'tricks': 'tips and tricks',
    'patches': 'patch',
    'patching': 'patch',
    'tasks': 'task',
    'monitored': 'monitoring',
    'monitor': 'monitoring',
    'sorting': 'sort',
    'sorted': 'sort',
    'sorter': 'sort',
    'sortable': 'sort',
    'profiles': 'profile',
    'profiling': 'profile',
    'library': 'lib',
    'libraries': 'lib',
    'libs': 'lib',
    'asynchronous': 'async',
    'deploy': 'deployement',
    'embedded': 'embed',
    'providers': 'provider',
    'backends': 'backend',
    'classes': 'class',
    'dependencies': 'dependency',
    'notes': 'note',
    'colors': 'color',
    'config': 'conf',
    'configs': 'conf',
    'configuration': 'conf',
    'contacts': 'contact',
    'deploy': 'deployement',
    'exercices': 'exercise',
    'exercice': 'exercise',
    'exercises': 'exercise',
    'frameworks': 'framework',
    'jq': 'jquery',
    'miscellaneous': 'misc',
    'notification': 'notify',
    'notifier': 'notify',
    'packages': 'package',
    'slides': 'slide',
    'vimrc': 'vim',
    'vimfiles': 'vim',
    'dotvim': 'vim',
    'uploader': 'upload',
    'tutorials': 'tutorial',
    'tabs': 'tab',
    'specification': 'specifications',
    'spec': 'specifications',
    'specs': 'specifications',
    'signals': 'signal',
    'secure': 'security',
    'rule': 'rules',
    'routes': 'route',
    'routing': 'route',
    'router': 'route',
    'robots': 'robot',
    'puppetlabs': 'puppet',
    'proj': 'project',
    'proto': 'prototype',
    'pres': 'presentation',
    'presentations': 'presentation',
    'patterns': 'pattern',
    'option': 'options',
    'objectivec': 'objective-c',
    'objc': 'objective-c',
    'objective': 'objective-c',
    'nav': 'navigation',
    'moosex': 'moose',
    'memcached': 'memcache',
    'learning': 'learn',
    'labs': 'lab',
    'katas': 'kata',
    'highlighter': 'highlight',
    'hacks': 'hack',
    'guides': 'guide',
    'games': 'game',
    'functions': 'function',
    'facebooker': 'facebook',
    'experiment': 'experiments',
    'erl': 'erlang',
    'env': 'environment',
    'dotemacs': 'emacs',
    'docrails': 'rails',
    'deployement': 'deployment',
    'components': 'component',
    'charts': 'chart',
    'cells': 'cell',
    'calculator': 'calc',
    'blueprints': 'blueprint',
    'attributes': 'attribute',
    'algorithms': 'algorithm',
    'achievements': 'achievement',
}

def split_into_words(text):
    """
    Split a text into words. Split words with spaces and capital letters.
    Ignore some predefined words.
    Ex: "some ExtJs addons" => some, ext, js, addons
    """
    # TODO : if many upper letter, consider as a whole word
    words, word = [], []
    def add_word(letters):
        if len(letters) <= 1:
            return
        word = ''.join(letters).lower()
        if word in get_ignore_words():
            return
        words.append(word)
    previous_upper = False
    for ch in text:
        start_new = False
        append = True
        if ch.isupper():
            start_new = not previous_upper
        else:
            if not ch in string.letters:
                start_new = True
                append = False
        if start_new and word:
            add_word(word)
            word = []
        if append:
            word.append(ch)
    if word:
        add_word(word)
    return words

text_types = dict(slug=20, description=0.1)

def repository_to_words(repository, words=None, return_words=True, repository_is_dict=False):
    """
    Get some text in a repository and get all words (a dict with each word
    with its weight)
    """
    if words is None:
        words = {}
    for text_type, text_weight in text_types.items():
        if repository_is_dict:
            text = repository.get(text_type, None)
        else:
            text = getattr(repository, text_type, None)
        if not text:
            continue
        text_words = set(split_into_words(text))
        for word in text_words:
            if word not in words:
                words[word] = 0
            words[word] += text_weight
    if return_words:
        return words

def manage_synonyms(words=None, return_words=True):
    """
    Take a list of words and return it after removing synonyms
    """
    if words is None:
        words = {}
    syns = {}
    for word, count in words.iteritems():
        if word in synonyms:
            syns[word] = count
    for syn, count in syns.iteritems():
        good = synonyms[syn]
        if good not in words:
            words[good] = 0
        words[good] += count
        del words[syn]
    if return_words:
        return words

def repositories_to_words(queryset, words=None, return_words=True):
    """
    Taking a list of repositories and get all words as a dict with each word
    and its weight
    """
    if words is None:
        words = {}
    qs = queryset.values('slug', 'description', 'readme')
    for repository in qs:
        repository_to_words(repository, words, False, True)
    manage_synonyms(words, False)
    if return_words:
        return words

def sort_words(words, limit=1000, return_format=None):
    """
    Keep only some words
    """
    if return_format not in ('dict', 'tuple', 'set'):
        return_format = 'set'
    sorted_words = sorted(((word, count) for word, count in words.iteritems() if count > limit), key=lambda w: w[1], reverse=True)
    if return_format == 'set':
        return set(word for word, count in sorted_words)
    if return_format == 'tuple':
        return sorted_words
    return dict(sorted_words)

def get_tags_for_repository(repository, all_tags, repository_is_dict=False):
    """
    Given a list of tags, check for them in a repository and return the found
    ones.
    If you call this for a big list of repositories, you can pass "slug" and
    "description" in a dict (using values in your queryset instead of a whole
    one)
    """
    tags_dict = manage_synonyms(repository_to_words(repository, repository_is_dict=repository_is_dict))
    tags_ok = all_tags.intersection(set(tags_dict.keys()))
    for tag in tags_dict.keys():
        if tag not in tags_ok:
            del tags_dict[tag]
    return tags_dict

def add_tags(tags, official=False, check_duplicates=True):
    """
    Add all tags in database. Set check_duplicates to False if you are SURE no
    tags already in db
    """
    from tagging.models import Tag as TaggingTag
    if check_duplicates:
        add = lambda t: TaggingTag.objects.get_or_create(slug=t, defaults=dict(name=t, official=official))
    else:
        add = lambda t: TaggingTag.objects.create(slug=t, name=t, official=official)
    for tag in tags:
        result = add(tag)
        # if already exists and we say it's official : update it
        if check_duplicates and official:
            tag_obj, created = result
            if not created and not tag_obj.official:
                tag_obj.official = True
                tag_obj.save()

RE_PARSE_TAGS = re.compile('"(.+?)"|,')
def parse_tags(tagstring):
    """
    Parse tags using a simple regular expression (same result as
    replace taggit.utils.parse_tags but with kept order)
    """
    return [word.strip() for word in RE_PARSE_TAGS.split(tagstring) if word and word.strip()]

def edit_string_for_tags(tags):
    """
    Replace taggit.utils.edit_string_for_tags by keeping order
    """
    names = []
    for tag in tags:
        name = tag.name
        if u',' in name or u' ' in name:
            names.append('"%s"' % name)
        else:
            names.append(name)
    return u', '.join(names)
