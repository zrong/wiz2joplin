##############################
# w2j.wiz
# 处理为知笔记相关
##############################

from os import PathLike
from typing import Any, Optional
from pathlib import Path
import sqlite3
from zipfile import ZipFile, BadZipFile

from w2j import logger, work_dir as default_work_dir
from w2j.parser import parse_wiz_html, tots, WizInternalLink, WizImage


class WizAttachment(object):
    """ 为知笔记附件

    在为知笔记中，附件属于一种资源，拥有自己的 guid
    """
    # 附件的 guid
    guid: str = None

    # 附件所属的文档 guid
    doc_guid: str = None

    # 附件的名称，一般是文件名
    name: str = None

    # 附件在硬盘上的文件名，格式为 {guid}name
    file_name: str = None

    # 附件的修改时间
    modified: int = 0

    # 附件的文件名所在地
    file: Path = None

    def __init__(self, guid: str, doc_guid: str, name: str, modified: str, attachments_dir: Path, check_file: bool = False) -> None:
        self.guid = guid
        self.doc_guid = doc_guid
        self.name = name
        self.modified = tots(modified)
        self.file_name =f'{{{self.guid}}}{self.name}'

        self.file = attachments_dir.joinpath(self.file_name)
        if check_file:
            self.check_file()
    
    def check_file(self):
        """ 检测附件是否存在
        """
        if not self.file.exists():
            raise FileNotFoundError(f'找不到文件 {self.file_name}')

    def __repr__(self) -> str:
        return f'<WizAttachment {self.guid}, {self.name}, {self.modified}>'


class WizTag(object):
    """ 为知笔记 TAG
    """
    # tag 的 guid
    guid: str = None

    name: str = None

    modified: int = 0

    def __init__(self, guid, name, modified) -> None:
        self.guid = guid
        self.name = name
        self.modified = tots(modified)

    def __repr__(self) -> str:
        return f'<WizTag {self.guid}, {self.name}, {self.modified}>'


class WizDocument(object):
    """ 为知笔记文档
    """
    # 文档的 guid
    guid: str = None
    title: str = None

    # 文件夹，为知笔记的文件夹就是一个用 / 分隔的字符串
    location: str = None

    # 保存一个 Folder 对象，这个对象在 Adapter 进行 Location 到 Folder 的转换之后才会填充
    folder: Any = None
    
    url: str = None # 如果文档是采集的，则这个地址为文档的采集url

    created: int = 0

    modified: int = 0

    # 从数据库中读取的附件数量，如果大于 0 说明这个文档有附件
    attachment_count: int = 0

    # 文档压缩包
    note_file: Path = None

    # 文档压缩包解压到的路径
    note_extract_dir: Path = None

    # 文档解压到的主文件夹
    documents_dir: Path

    # 文档正文
    body: str = None

    # markdown，默认为 markdown
    is_markdown: bool = True

    # 文档的标签
    tags: list[WizTag] = []

    # 文档的附件
    attachments: list[WizAttachment] = []

    # 包含在为知笔记文档中的图像文件，需要在文档正文中使用正则提取
    images: list[WizImage] = []

    # 包含在为知笔记文档中的内部链接，需要在文档征文中使用正则提取
    internal_links: list[WizInternalLink] = []

    def __init__(self, guid: str, title: str, location: str, url: str, created: str, modified: str, attachment_count: int, notes_dir: Path, documents_dir: Path, check_file: bool = False) -> None:
        self.guid = guid
        self.location = location
        self.url = url
        self.created = tots(created)
        self.modified = tots(modified)
        self.attachment_count = attachment_count

        self.documents_dir = documents_dir

        self.is_markdown = title.endswith('.md')
        if self.is_markdown and len(title) > 3:
            self.title = title[:-3]
        else:
            self.title = title

        self.note_file = notes_dir.joinpath(f'{{{self.guid}}}')
        if check_file:
            self.check_note_file()

    def check_note_file(self):
        if self.note_file is None or not self.note_file.exists():
            raise FileNotFoundError(f'找不到 note 文件 {self.note_file}！')

    def resolve_attachments(self, attachments: list[WizAttachment]) -> None:
        self.attachments = attachments
        if len(self.attachments) != self.attachment_count:
            raise ValueError(f'附件数量不匹配 {len(self.attachments)} != {self.attachment_count}！')
        # 检测所有附件文件是否存在
        try:
            for attach in self.attachments:
                attach.check_file()
        except FileNotFoundError as e:
            msg = f'{e!s}，请检查文档 {self.title}'
            raise FileNotFoundError(msg)
        
    def resolve_tags(self, tags: list[WizTag]) -> None:
        self.tags = tags

    def _extract_zip(self) -> None:
        """ 解压缩当前文档的 zip 文件到 work_dir，以 guid 为子文件夹名称
        """
        self.note_extract_dir = self.documents_dir.joinpath(self.guid)
        # 如果目标文件夹已经存在，就不解压了
        if self.note_extract_dir.exists():
            # logger.info(f'{self.note_extract_dir!s} |{self.title}| 已经存在，跳过。')
            return
        try:
            zip_file = ZipFile(self.note_file)
            zip_file.extractall(self.note_extract_dir)
        except BadZipFile as e:
            msg = f'ZIP 文件错误，可能是需要密码。 {self.note_file!s} |{self.title}|'
            raise BadZipFile(msg)
            # logger.info(msg)

    def _parse_wiz_note(self) -> None:
        """ 解析 index.html 文件
        """
        if self.note_extract_dir is None:
            raise FileNotFoundError(f'请先解压缩文档 {self.note_file!s} |{self.title}|')

        self.body, self.internal_links, self.images = parse_wiz_html(self.note_extract_dir, self.title)

    def resolve_body(self) -> None:
        """ 解压文档压缩包，解析文档正文中的图像文件，将其转换为 WizImage
        将正文存入 body
        """
        self.check_note_file()
        self._extract_zip()
        self._parse_wiz_note()

    def resolve(self, attachments: list[WizAttachment], tags: list[WizTag]) -> None:
        self.resolve_attachments(attachments)
        self.resolve_tags(tags)
        self.resolve_body()

    def __repr__(self):
        return f'<w2j.wiz.WizDocument {self.note_file.resolve()} |{self.title}| tags: {len(self.tags)} attachments: {len(self.attachments)} markdown: {self.is_markdown}>'


class DataDir(object):
    """ 保存 data 文件夹中的 Path 对象
    """
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

        self.attachments_dir = self.data_dir.joinpath('attachments/')
        if not self.attachments_dir.is_dir():
            raise FileNotFoundError(f'找不到文件夹 {self.attachments_dir.resolve()}！')

        self.notes_dir = self.data_dir.joinpath('notes/')
        if not self.notes_dir.is_dir():
            raise FileNotFoundError(f'找不到文件夹 {self.notes_dir.resolve()}！')

        self.index_db = self.data_dir.joinpath('index.db')
        if not self.index_db.exists():
            raise FileNotFoundError(f'找不到数据库 {self.index_db.resolve()}！')

        self.wizthumb_db = self.data_dir.joinpath('wizthumb.db')
        if not self.wizthumb_db.exists():
            raise FileNotFoundError(f'找不到数据库 {self.wizthumb_db.resolve()}！')

    def _get_one_document(self, guid: str) -> tuple[Optional[tuple], list, list]:
        conn = sqlite3.connect(self.index_db)
        cur = conn.cursor()

        sql = '''SELECT
        DOCUMENT_GUID, DOCUMENT_TITLE, DOCUMENT_LOCATION, DOCUMENT_URL, DT_CREATED, DT_MODIFIED, DOCUMENT_ATTACHEMENT_COUNT
        FROM WIZ_DOCUMENT
        WHERE DOCUMENT_GUID = ?
        '''
        cur.execute(sql, (guid, ))
        document_row = cur.fetchone()
        attachment_rows  = []
        tag_rows = []

        if document_row:
            sql = '''SELECT
            ATTACHMENT_GUID, DOCUMENT_GUID, ATTACHMENT_NAME, DT_INFO_MODIFIED
            FROM WIZ_DOCUMENT_ATTACHMENT
            WHERE DOCUMENT_GUID = ?
            '''
            cur.execute(sql, (guid, ))
            attachment_rows = cur.fetchall()

            sql = '''SELECT
            WIZ_TAG.TAG_GUID, WIZ_TAG.TAG_NAME, WIZ_TAG.DT_MODIFIED
            FROM WIZ_DOCUMENT_TAG INNER JOIN WIZ_TAG
            ON WIZ_DOCUMENT_TAG.TAG_GUID = WIZ_TAG.TAG_GUID
            WHERE WIZ_DOCUMENT_TAG.DOCUMENT_GUID = ?
            '''
            cur.execute(sql, (guid, ))
            tag_rows = cur.fetchall()

        conn.close()
        return document_row, attachment_rows, tag_rows

    def _get_all_document(self):
        """ 获取 WIZ_DUCUMENT 的所有记录
        """
        conn = sqlite3.connect(self.index_db)
        cur = conn.cursor()
        cur.execute('SELECT DOCUMENT_GUID, DOCUMENT_TITLE, DOCUMENT_LOCATION, DOCUMENT_URL, DT_CREATED, DT_MODIFIED, DOCUMENT_ATTACHEMENT_COUNT FROM WIZ_DOCUMENT')
        rows = cur.fetchall()
        conn.close()
        return rows

    def _get_all_attachment(self) -> list:
        """ 获取 WIZ_DOCUMENT_ATTACHMENT 的所有记录
        """
        conn = sqlite3.connect(self.index_db)
        cur = conn.cursor()
        cur.execute('SELECT ATTACHMENT_GUID, DOCUMENT_GUID, ATTACHMENT_NAME, DT_INFO_MODIFIED FROM WIZ_DOCUMENT_ATTACHMENT')
        rows = cur.fetchall()
        conn.close()
        return rows

    def _get_all_tag(self) -> list:
        """ 获取 WIZ_TAG 的所有记录
        """
        conn = sqlite3.connect(self.index_db)
        cur = conn.cursor()
        cur.execute('SELECT TAG_GUID, TAG_NAME, DT_MODIFIED FROM WIZ_TAG')
        rows = cur.fetchall()
        conn.close()
        return rows

    def _get_all_document_tag(self) -> list:
        """ 获取 WIZ_DOCUMENT_TAG 的所有记录
        """
        conn = sqlite3.connect(self.index_db)
        cur = conn.cursor()
        cur.execute('SELECT DOCUMENT_GUID, TAG_GUID FROM WIZ_DOCUMENT_TAG')
        rows = cur.fetchall()
        conn.close()
        return rows

    def __repr__(self):
        return f'<w2j.wiz.DataDir {self.data_dir.resolve()}>'


class WizStorage(object):
    """ 保存所有为知笔记的数据
    """
    # 工作文件夹所在地址，临时文件会置于工作文件夹中
    work_dir: Path

    # 为知笔记文档解压到这个文件夹
    documents_dir: Path

    wiznote_dir: Path
    user_id: str
    user_dir: Path
    group_dir: Path

    # 是否为 group 仓库
    is_group_storage: bool = False

    data_dir: DataDir

    # 所有的 TAG
    tags: list[WizTag] = []
    # 键名为文档的 guid，键值为该该文档中的 Tag
    tags_in_document: dict[str, list[WizTag]] = {}

    # 所有的附件
    attachments: list[WizAttachment] = []
    # 键名为文档的 guid，键值为该该文档中的 Attachment
    attachments_in_document: dict[str, list[WizAttachment]] = {}

    # 所有的图片
    images: list[WizImage] = []
    # 键名为文档的 guid，键值为该该文档中的 Image
    images_in_document: dict[str, list[WizImage]] = {}

    # 所有的文档
    documents: list[WizDocument] = []

    def __init__(self, user_id: str, wiznote_dir: Path, is_group_storage: bool = False, work_dir: Path = None):
        """ 定义位置笔记文件夹
        :param user_id: 帐号邮箱
        :param winznote_dir: 帐号所在文件夹
        :param work_dir: 工作文件夹，用于解压文件等操作，若不提供则使用临时文件夹
        """
        self.work_dir = work_dir or default_work_dir

        # 创建专门解压缩位置文档的文件夹
        self.documents_dir = self.work_dir.joinpath('documents')
        if not self.documents_dir.exists():
            self.documents_dir.mkdir(parents=True)

        self.wiznote_dir = wiznote_dir
        self.user_id = user_id
        self.user_dir = self.wiznote_dir.joinpath(user_id)
        self.group_dir = self.user_dir.joinpath('group')
        self.is_group_storage = is_group_storage

        # data 的根文件夹
        root_data_dir = DataDir(self.user_dir.joinpath('data/'))
        # 获取 group 仓库，位于 data 根文件夹之下
        if self.is_group_storage:
            biz_guid = self._get_biz_guid(root_data_dir.index_db)
            self.data_dir = DataDir(self.group_dir.joinpath(biz_guid))
        else:
            self.data_dir = root_data_dir

    def _get_biz_guid(self, index_db: Path) -> str:
        """ 通过一次查询获取 user 的 guid
        """
        conn = sqlite3.connect(index_db)
        cur = conn.cursor()
        cur.execute('SELECT BIZ_GUID FROM WIZ_USER where USER_ID=?', (self.user_id,))
        row = cur.fetchone()
        conn.close()
        if row is not None:
            return row[0]
        return None

    def _build_tags(self) -> tuple[list[WizTag], dict[str, list[WizTag]]]:
        """ 根据数据库内容构建所有的 tag 列表
        创建一个 dict ，键名为文档 guid，键值为该文档中的 Tag 列表
        返回这两个列表
        """
        tag_rows = self.data_dir._get_all_tag()
        tags: list[WizTag] = []
        # 创建一个临时的 dict 用于查找 tag guid
        key_tags: dict[str, WizTag] = {}
        for row in tag_rows:
            tag = WizTag(*row)
            tags.append(tag)
            key_tags[tag.guid] = tag

        tag_in_doc_rows = self.data_dir._get_all_document_tag()
        tags_dict: dict[str, list[WizTag]] = {}

        for row in tag_in_doc_rows:
            doc_guid = row[0]
            tag_guid = row[1]

            if tags_dict.get(doc_guid) is None:
                tags_dict[doc_guid] = []

            # 如果在 key_tags 中找不到 tag_guid 会报错，此时就需要检查为知笔记中的 tag 设置了
            tags_dict[doc_guid].append(key_tags[tag_guid])
        return tags, tags_dict

    def _build_attachments(self) -> tuple[list[WizAttachment], dict[str, list[WizAttachment]]]:
        """ 根据数据库内容构建所有的 attachemnt 列表
        创建一个 dict ，键名为文档 guid，键值为该文档中的 attachment 列表
        返回这两个列表
        """
        rows = self.data_dir._get_all_attachment()
        attachments: list[WizAttachment] = []

        attachments_in_document: dict[str, list[WizAttachment]] = {}

        for row in rows:
            attachment = WizAttachment(*row, self.data_dir.attachments_dir)
            attachments.append(attachment)
            if attachments_in_document.get(attachment.doc_guid) is None:
                attachments_in_document[attachment.doc_guid] = []
            attachments_in_document[attachment.doc_guid].append(attachment)
        return attachments, attachments_in_document

    def build_documents(self) -> list[WizDocument]:
        """ 根据数据库内容构建所有的 document 列表
        """
        rows = self.data_dir._get_all_document()

        attachments, attachments_in_doc = self._build_attachments()
        tags, tags_in_doc = self._build_tags()

        self.attachments = attachments
        self.attachments_in_document = attachments_in_doc
        self.tags = tags
        self.tags_in_document = tags_in_doc

        documents: list[WizDocument] = []
        for row in rows:
            document = WizDocument(*row, self.data_dir.notes_dir, self.documents_dir, check_file=True)
            document.resolve(
                self.attachments_in_document.get(document.guid, []),
                self.tags_in_document.get(document.guid, [])
            )
            documents.append(document)
        return documents

    def build_document(self, guid: str) -> WizDocument:
        """ 构建一个 document
        """
        document_row, attachment_rows, tag_rows = self.data_dir._get_one_document(guid)
        if not document_row:
            raise ValueError(f'找不到文档 {guid}！')

        attachments: list[WizAttachment] = []
        for row in attachment_rows:
            attachments.append(WizAttachment(*row, self.data_dir.attachments_dir, check_file=False))
        
        tags: list[WizTag] = []
        for row in tag_rows:
            tags.append(WizTag(*row))

        document = WizDocument(*document_row, self.data_dir.notes_dir, self.documents_dir, check_file=True)
        document.resolve(attachments, tags)
        return document

    def resolve(self) -> None:
        """ 解析所有文档并保存相关数据
        调用此方法后，所有数据安全并可用
        """
        self.documents = self.build_documents()
        
    def clear(self) -> None:
        """ 删除解压的临时文件夹
        """
        self.documents_dir.unlink()

