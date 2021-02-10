##############################
# w2j.joplin
# 处理 Joplin 相关
##############################

from w2j import logger

class JoplinFolder(object):
    """ Joplin 中的 notebook
    """
    name = 'folder'
    type_ = 2

    id: str = None
    title: str = None
    parent_id: str = None
    created_time: int = None
    updated_time: int = None

    def __repr__(self) -> str:
        return f'<JoplinFolder {self.id}, {self.title}, parent_id: {self.parent_id}>'


class JoplinResource(object):
    """ Joplin 中的 Resource
    """
    name = 'resource'
    type_ = 4

    id: str = None
    title: str = None
    filename: str = None
    file_extension: str = None
    created_time: int = None
    updated_time: int = None

    def __repr__(self) -> str:
        return f'<JoplinResource {self.id}, {self.title}>'


class JoplinTag(object):
    """ Joplin 中的 tag
    """
    name = 'tag'
    type_ = 5

    id: str = None
    title: str = None
    parent_id: str = None
    created_time: int = None
    updated_time: int = None

    def __repr__(self) -> str:
        return f'<JoplinTag {self.id}, {self.title}, parent_id: {self.parent_id}>'


class JoplinNote(object):
    """ 创建一个 Joplin 的 Note 类
    """

    # 为知笔记中的 document guid，36 位
    guid: str = None

    # Joplin 中的 note id，32 位，去掉 guid 中的 hyphen
    id: str = None

    # Joplin 中的 note title
    title: str = None

    # Joplin 中的 body
    body: str = None

    # Joplin 中的创建时间戳，毫秒
    created_time: int = None

    # Joplin 中的更新时间戳，毫秒
    updated_time: int = None

    # Joplin 中的文章 url
    source_url: str = None

    # 1 代表 markdown，2代表 html
    markup_language: int = 1

    tags: list[JoplinTag] = []
    resources: list[JoplinResource] = []
    folder: JoplinFolder = None

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f'<JoplinNote {self.id}, {self.title}, tag: {len(self.tags)}, resource: {len(self.resources)}, folder: {len(self.folder)}>'


class JoplinStorage(object):
    pass