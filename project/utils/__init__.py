# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from datetime import datetime
from time import mktime

def dt2timestamp(dt):
    return int(mktime(dt.timetuple()))

def now_timestamp():
    return dt2timestamp(datetime.utcnow())
