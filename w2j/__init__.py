##############################
# w2j =  Wiznote to Joplin
# https://github.com/zrong/wiz2joplin
##############################

import logging
import sys

__autho__ = 'zrong'
__version__ = '0.1'

logger = logging.Logger('w2j')
logger.addHandler(logging.StreamHandler(sys.stderr))


class Note(object):
    """ 创建一个兼容 Wiz 和 Joplin 的 Note
    """

    # 为知笔记中的 document guid
    guid = None

    # Joplin 中的 note id
    id = None

    # Joplin 中的 note title
    title = None

    # Joplin 中的 body
    body = None

    # Joplin 中的创建时间戳，毫秒
    created_time = None

    # Joplin 中的更新时间戳，毫秒
    updated_time = None

    # Joplin 中的文章 url
    source_url = None

    # 1 代表 markdown，2代表 html
    markup_language = 1

    def __init__(self):
        pass