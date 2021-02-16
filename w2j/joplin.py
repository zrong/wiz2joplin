##############################
# w2j.joplin
#
# 处理 Joplin 相关
# 结构查看 https://joplinapp.org/api/references/rest_api/
##############################


from typing import Optional

from attr import field
from w2j import logger
import httpx


class JoplinFolder(object):
    """ Joplin 中的 notebook
    """
    name = 'folder'
    type_ = 2

    # Folder 在 Joplin 数据库中的 guid
    id: str = None

    # Folder 名称
    title: str = None

    # 创建时间戳
    created_time: int = 0

    # 更新时间戳
    updated_time: int = 0

    # 如果有父 Folder，则值为其 ID
    parent_id: str = None

    # 所有必须的 fields 名称
    fields = ['id', 'title', 'created_time', 'updated_time', 'parent_id']

    def __init__(self, id: str, title: str, created_time: int, updated_time: int, parent_id: Optional[str] = None, **kwargs) -> None:
        self.id = id
        self.title = title
        self.created_time = created_time
        self.updated_time = updated_time
        self.parent_id = parent_id

    @classmethod
    def fields_str(cls) -> str:
        return ','.join(cls.fields)

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
    created_time: int = 0
    updated_time: int = 0

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

    # 所有必须的 fields 名称
    fields = ['id', 'title', 'created_time', 'updated_time', 'body', 'markup_lanaguage']

    @classmethod
    def fields_str(cls):
        return ','.join(cls.fields)

    def __repr__(self) -> str:
        return f'<JoplinNote {self.id}, {self.title}, tag: {len(self.tags)}, resource: {len(self.resources)}, folder: {len(self.folder)}>'


class JoplinDataAPI(object):

    host: str = '127.0.0.1'
    port: int = 41184
    token: str = '7e04c3e264c6d65e32da5567e6ba1fcc20d68c82c96acc1c325099d42c53a98e2ee5b2d65a8088c11422a15e3855bdeba91c99200396b710d38a057798a699b6'
    base_url: str = None
    
    client: httpx.Client = None

    def __init__(self, host: str = '127.0.0.1', port: int = 41184, token: str = '7e04c3e264c6d65e32da5567e6ba1fcc20d68c82c96acc1c325099d42c53a98e2ee5b2d65a8088c11422a15e3855bdeba91c99200396b710d38a057798a699b6') -> None:
        self.host = host
        self.port = port
        self.token = token
        self.base_url = f'http://{self.host}:{self.port}'
        self.client = httpx.Client(base_url=self.base_url)

    def _build_query(self, **kwargs):
        return httpx.QueryParams(token=self.token, **kwargs)

    def _check_pagination(self, page: int, paginated_resp: httpx.Response) -> tuple[list, bool, int]:
        """ 专门处理分页
        :returns: items, has_more, next_page
        """
        data = paginated_resp.json()
        if data.get('error'):
            raise ValueError(data['error'])
        has_more = data['has_more']
        next_page = page
        if has_more:
            next_page += 1
        return data['items'], has_more, next_page

    def close(self):
        self.client.close()

    def ping(self) -> bool:
        resp = self.client.get('/ping')
        return resp.text == 'JoplinClipperServer'

    def search(self, query: str, type_: str) -> httpx.Response:
        return self.client.get('/search')

    def get_folder(self, guid: str) -> JoplinFolder:
        """ 根据 guid 获取 folder
        """
        query = self._build_query()
        resp = self.client.get(f'/folders/{guid!s}', params=query)
        data = resp.json()
        if data.get('error'):
            raise ValueError(data['error'])
        return JoplinFolder(**data)

    # https://joplinapp.org/api/references/rest_api/#pagination
    # https://joplinapp.org/api/references/rest_api/#get-folders
    # order_by=updated_time&order_dir=ASC&limit=10&page=2
    def get_folders(self, order_by: str='updated_time', order_dir: str='ASC', limit: int=100, page: int=1) -> \
        tuple[ list[JoplinFolder], bool, int]:
        """ 获取一组 folder，支持分页
        :returns: joplin folder list, has_more, next_page
        """
        folders: list[JoplinFolder] = []

        def __build_query(page: int) -> httpx.QueryParams:
            return self._build_query(order_by=order_by, order_dir=order_dir, page=page, limit=limit, fields=JoplinFolder.fields_str())

        def __get_folders(query: httpx.QueryParams) -> tuple[bool, int]:
            resp = self.client.get('/folders', params=query)
            items, has_more, next_page = self._check_pagination(int(query.get('page')), resp)
            for item in items:
                folders.append(JoplinFolder(**item))
            return has_more, next_page

        if page > 0:
            query = __build_query(page)
            has_more, next_page = __get_folders(query)
            return folders, has_more, next_page

        # 小于等于 0 的 page 代表获取全部
        page = 1
        query = __build_query(page)
        has_more, next_page = __get_folders(query)
        while(has_more):
            query = __build_query(next_page)
            has_more, next_page = __get_folders(query)
        return folders, has_more, next_page

    def get_folder_note(self, guid: str) -> list[JoplinFolder]:
        """ 获取一个 folder 下的所有 note
        """
        query = self._build_query(fields=JoplinNote.fields_str())
        resp = self.client.get('/folders/{guid}/notes', params=query)
        return JoplinNote(**resp.json())

    def post_folder(self, **kwargs) -> JoplinFolder:
        """ 创建一个新的 folder
        """
        query = self._build_query()
        resp = self.client.post('/folders', params=query, json=kwargs)
        data = resp.json()
        if data.get('error'):
            raise ValueError(data['error'])
        return JoplinFolder(**data)
