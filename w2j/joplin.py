##############################
# w2j.joplin
#
# 处理 Joplin 相关
# 结构查看 https://joplinapp.org/api/references/rest_api/
##############################


import json
from pathlib import Path
from typing import Optional, Union

import httpx
import sqlite3

from w2j import logger
from w2j.parser import JoplinInternalLink


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

    # 1 附件，2 文中图像
    resource_type: int

    # 所有必须的 fields 名称
    fields = ['id', 'title', 'created_time', 'updated_time', 'filename', 'file_extension']

    @classmethod
    def fields_str(cls) -> str:
        return ','.join(cls.fields)

    def __init__(self, id: str, title: str, filename: str, created_time: int, resource_type: int, **kwargs) -> None:
        self.id = id
        self.title = title
        self.filename = filename
        self.resource_type = resource_type
        self.created_time = created_time
        if kwargs.get('file_extension'):
            self.file_extension = kwargs.get('file_extension')
        if kwargs.get('updated_time'):
            self.updated_time = kwargs.get('updated_time')

    def __repr__(self) -> str:
        return f'<JoplinResource {self.id} |{self.title}|{self.resource_type} {self.filename}>'


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

    # 所有必须的 fields 名称
    fields = ['id', 'title', 'created_time', 'updated_time']

    @classmethod
    def fields_str(cls):
        return ','.join(cls.fields)

    def __init__(self, id: str, title: str, created_time:int, updated_time: int = 0, **kwargs) -> None:
        self.id = id
        self.title = title
        self.created_time = created_time
        self.updated_time = created_time if updated_time == 0 else updated_time

    def __repr__(self) -> str:
        return f'<JoplinTag {self.id}, {self.title}, parent_id: {self.parent_id}>'


class JoplinNote(object):
    """ 创建一个 Joplin 的 Note 类
    """
    # Joplin 中的 note id，32 位
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

    location: str = ''
    parent_id: str = ''

    tags: dict[str, JoplinTag] = {}
    resources: dict[str, JoplinResource] = {}
    internal_links: dict[JoplinInternalLink] = {}
    folder: JoplinFolder = None

    # 所有必须的 fields 名称
    fields = ['id', 'title', 'parent_id', 'created_time', 'updated_time', 'body', 'source_url', 'markup_lanaguage']

    def __init__(self, id: str, title: str, parent_id: str, markup_language: int, **kwargs) -> None:
        self.id = id
        self.title = title
        self.parent_id = parent_id
        self.markup_language = markup_language
        if kwargs.get('location'):
            self.location = kwargs.get('location')
        if kwargs.get('source_url'):
            self.source_url = kwargs.get('source_url')
        if kwargs.get('created_time'):
            self.created_time = kwargs.get('created_time')
        if kwargs.get('updated_time'):
            self.updated_time = kwargs.get('updated_time')

    @classmethod
    def fields_str(cls):
        return ','.join(cls.fields)

    def __repr__(self) -> str:
        return f'<JoplinNote {self.id}, {self.title}, tag: {len(self.tags)}, resource: {len(self.resources)}, folder: {len(self.folder)}>'


class JoplinDataAPI(object):

    host: str
    port: int
    token: str
    base_url: str
    
    client: httpx.Client = None

    def __init__(self, host: str = '127.0.0.1', port: int = 41184, token: str = 'ad9b597aac8c9fa2083cb23c4354eb589b1252e6a366185d94795077ed076dfdb312c22b8640a05e5af7b784d65d831a429771e3cc2bcbe3f9cdac441d6fcca6') -> None:
        self.host = host
        self.port = port
        self.token = token
        self.base_url = f'http://{self.host}:{self.port}'
        self.client = httpx.Client(base_url=self.base_url, timeout=100)

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
        resp = self.client.get(f'/folders/{guid}', params=query)
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
        logger.info(f'向 Joplin 增加 folder {kwargs}')
        resp = self.client.post('/folders', params=query, json=kwargs)
        data = resp.json()
        if data.get('error'):
            logger.error(data['error'])
            raise ValueError(data['error'])
        return JoplinFolder(**data)

    def post_tag(self, **kwargs) -> JoplinTag:
        """ 创建一个新的 tag
        """
        query = self._build_query()
        logger.info(f'向 Joplin 增加 tag {kwargs}')
        resp = self.client.post('/tags', params=query, json=kwargs)
        data = resp.json()
        if data.get('error'):
            logger.error(data['error'])
            raise ValueError(data['error'])
        return JoplinTag(**data)

    def get_tag(self, guid: str) -> JoplinTag:
        """ 根据 guid 获取 tag
        """
        query = self._build_query(fields=JoplinTag.fields_str())
        resp = self.client.get(f'/tags/{guid}', params=query)
        data = resp.json()
        logger.info(f'从 Joplin 获取 tag {guid}: {data}')
        if data.get('error'):
            logger.error(data['error'])
            raise ValueError(data['error'])
        return JoplinTag(**data)

    def post_resource(self, file: Path, resource_type: int, **kwargs) -> JoplinResource:
        """ 创建一个新的 resources
        """
        query = self._build_query()
        files = {'data': open(file, 'rb')}
        # 经过测试 props 中只有 title 和 id 有作用，其他的参数都无效
        data = {'props': json.dumps(kwargs)}
        logger.info(f'向 Joplin 增加 resource {file} {kwargs}')
        resp = self.client.post('/resources', params=query, files=files, data=data)
        data = resp.json()
        if data.get('error'):
            logger.error(data['error'])
            raise ValueError(data['error'])
        return JoplinResource(**data, resource_type=resource_type)

    def get_resource(self, guid: str) -> JoplinResource:
        """ 根据 guid 获取 resource
        """
        query = self._build_query(fields=JoplinResource.fields_str())
        resp = self.client.get(f'/resources/{guid}', params=query)
        data = resp.json()
        logger.info(f'从 Joplin 获取 resource {guid}: {data}')
        if data.get('error'):
            logger.error(data['error'])
            raise ValueError(data['error'])
        return JoplinResource(**data)

    def post_note(self, id: str, title: str, body: str, 
        is_markdown: bool, parent_id: str, source_url: str) -> JoplinNote:
        """ 创建一个新的 Note
        隐藏的 Joplin 参数：通过抓包 Joplin WebClipper
        
        complete Page Html
        source_command
        {
            'name': 'completePageHtml',
            'preProcessFor': 'html'
        }
        convert_to = html

        simplified Page Html
        source_command
        {
            'name': 'simplifiedPageHtml',
        }
        convert_to = markdown

        complete page
        source_command = markdown
        {
            'name': 'completePageHtml',
            'preProcessFor': 'markdown'
        }
        convert_to = markdown
        """
        kwargs = {
            'id': id,
            'title': title,
            'parent_id': parent_id,
            'markup_language': 1,
        }
        if source_url:
            kwargs['source_url'] = source_url
        if is_markdown:
            kwargs['body'] = body
        else:
            # 使用 joplin 的功能将所有的 html 都转换成 markdown
            kwargs['body_html'] = body
            kwargs['convert_to'] = 'markdown'
            kwargs['source_command'] = {
                'name': 'simplifiedPageHtml',
            }

        query = self._build_query()
        logger.info(f'向 Joplin 增加 note {kwargs}')
        resp = self.client.post('/notes', params=query, json=kwargs)
        data = resp.json()
        if data.get('error'):
            logger.error(data['error'])
            raise ValueError(data['error'])
        return JoplinNote(**data)

    def get_note(self, guid: str) -> JoplinNote:
        """ 根据 guid 获取 note
        """
        query = self._build_query(fields=JoplinNote.fields_str())
        resp = self.client.get(f'/notes/{guid}', params=query)
        data = resp.json()
        logger.info(f'从 Joplin 获取 note {guid}: {data}')
        if data.get('error'):
            raise ValueError(data['error'])
        return JoplinNote(**data)


class JoplinStorage(object):
    """ 保存 Joplin 数据
    """
    # joplin 资源所在文件夹
    joplin_dir: Path

    # joplin 主数据库
    db_file: Path

    def __init__(self, joplin_dir: Path) -> None:
        self.joplin_dir = joplin_dir
        self.db_file = self.joplin_dir.joinpath('database.sqlite')

    def update_time(self, wiz_document_times: list[dict[str, Union[str, int]]]):
        """ 根据为知笔记的文章更新时间修改 Joplin note 的时间
        """
        self.conn = sqlite3.connect(self.db_file)
        sql = "UPDATE notes SET created_time=:created_time, updated_time=:updated_time, user_created_time=:created_time, user_updated_time=:updated_time WHERE id=:id;"
        # for wdt in wiz_document_times:
        #     print(wdt)
        cursor = self.conn.executemany(sql, wiz_document_times)
        print(cursor.rowcount)
        self.conn.commit()
        self.conn.close()