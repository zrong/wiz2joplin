##############################
# w2j.adapter
#
# 适配器，将解析后的为知笔记对象装备成 joplin 笔记对象
##############################

from pathlib import Path
from typing import Optional, Union
import json
import sqlite3

from w2j import logger, work_dir as default_work_dir
from w2j.wiz import WizDocument, WizAttachment, WizImage, WizInternalLink, WizTag, WizStorage
from w2j.joplin import JoplinNote, JoplinFolder, JoplinResource, JoplinTag, JoplinDataAPI
from w2j.parser import tojoplinid


class Location2Folder(object):
    """ 为知笔记的 Location 与 Joplin 的 Folder 之转换关系
    """
    # 为知笔记的全路径名称（包含 / 的所有部分）
    location: str

    # 当前目录的名称
    title: str

    # 为知笔记的父全路径名称
    parent_location: str

    # 1/2/3 来表示当前  Folder 处于第几级，顶级为 level1
    level: int

    # Joplin Folder guid，只有创建之后才会存在
    id: str

    # 父 Joplin Folder guid
    parent_id: str

    def __init__(self, location: str, title: str = None, parent_location: str = None, level: int = 0, id: str = None, parent_id: str = None, **kwargs) -> None:
        self.location = location

        if title is None:
            # 去掉头尾的 / 后使用 / 分隔
            titles = location[1:-1].split('/')

            self.level = len(titles)
            # 最后一个是当前目录
            self.title = titles[-1]
            # 有父目录
            if self.level > 1:
                self.parent_location = '/' + '/'.join(titles[:-1]) + '/'
            else:
                self.parent_location = None
        else:
            self.title = title
            self.parent_location = parent_location
            self.level = level

        self.id = id
        self.parent_id = parent_id

    def __conform__(self, protocol) -> str:
        if protocol is sqlite3.PrepareProtocol:
            return f'{self.location};{self.title};{self.parent_location};{self.level};{self.id};{self.parent_id}'
        return ''

    def __repr__(self) -> str:
        return f'<Location2Folder id: {self.id}, title: {self.title}, location: {self.location}, level: {self.level}, parent_location: {self.parent_location}>'


class L2FUtil():
    """ 处理 Location2Folder 对象
    """
    # 最大的级别
    max_level: int = 0

    # 将为知笔记转换到 Joplin 目录的结果存储到 dict 中
    db: dict[str, Location2Folder]

    # 转换过程中的专用数据库连接
    conn: sqlite3.Connection

    # lzf_db 的内容写入 json 文件中，避免每次都要重新生成 Folder，造成重复
    db_file: Path

    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """ 创建数据库
        """
        self.conn = sqlite3.connect(self.db_file)
        test_table = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?;"

        l2f_exists = self.conn.execute(test_table, ('l2f', )).fetchone()[0]
        note_exists = self.conn.execute(test_table, ('note', )).fetchone()[0]
        resource_exists = self.conn.execute(test_table, ('resource', )).fetchone()[0]
        internal_link_exists = self.conn.execute(test_table, ('internal_link', )).fetchone()[0]

        logger.info(f'表 l2f, note 是否存在: {l2f_exists}, {note_exists}')

        if not l2f_exists:
            # 保存 Location 和 Folder 的关系
            create_l2f_sql = """CREATE TABLE l2f (
                location TEXT NOT NULL,
                id TEXT,
                title TEXT NOT NULL,
                parent_location TEXT,
                parent_id TEXT,
                level INTEGER NOT NULL,
                PRIMARY KEY (location)
            );
            """
            self.conn.execute(create_l2f_sql)
        if not note_exists:
            # 处理过的文档会保存在这里，在这个表中能找到的文档说明已经转换成功了
            create_note_sql = """CREATE TABLE note (
                wiz_doc_guid TEXT not NULL,
                title TEXT not NULL,
                wiz_location TEXT NOT NULL,
                joplin_folder TEXT NOT NULL,
                markup_language INTEGER NOT NULL,
                PRIMARY KEY (wiz_doc_guid)
            );
            """
            self.conn.execute(create_note_sql)
        if not resource_exists:
            # 处理过的资源保存在这里，包括 image 和 attachment 资源
            create_resource_sql = """CREATE TABLE resource (
                resource_id TEXT not NULL,
                wiz_doc_guid TEXT not NULL,
                name TEXT not NULL,
                modified INTEGER not NULL,
                resource_type INTEGER NOT NULL,
                PRIMARY KEY (resource_id)
            );
            """
            self.conn.execute(create_resource_sql)

        if not internal_link_exists:
            # 保存为知笔记中的内链，使用 文档 guid 和 连接目标 guid 同时作为主键。链接目标 guid 为 joplin 格式
            internal_link_sql = """CREATE TABLE resource (
                wiz_doc_guid TEXT not NULL,
                link_resource_id TEXT not NULL,
                title TEXT not NULL,
                modified INTEGER not NULL,
                link_type INTEGER NOT NULL,
                PRIMARY KEY (wiz_doc_guid, link_resource_id)
            );
            """
            self.conn.execute(internal_link_sql)

    def close(self):
        self.conn.close()

    def build_location_to_top(self, location: str, document: Optional[WizDocument] = None):
        """ 构建一个 location 直到最顶端，并返回这个 location 对应的 l2f 对象
        """
        l2f_inst = self.db.get(location)
        if l2f_inst is None:
            l2f_inst = Location2Folder(location)
            self.db[location] = l2f_inst
            self.conn.execute(
                'INSERT INTO l2f(location, title, parent_location, level, id, parent_id) VALUES (:location, :title, :parent_location, :level, :id, :parent_id)',
                vars(l2f_inst)
            )
            self.conn.commit()
        if l2f_inst is not None and l2f_inst.parent_location is not None:
            # 递归调用时，不传递 document
            self.build_location_to_top(l2f_inst.parent_location, None)
        # 仅当创建「最低端 folder」的时候才会更新 document 中的引用
        if document is not None:
            document.folder = l2f_inst
        # 获取最大的 level
        if l2f_inst.level > self.max_level:
            self.max_level = l2f_inst.level

    def load_from_db(self):
        sql = 'SELECT location, title, parent_location, level, id, parent_id FROM l2f;'
        l2f_items = self.conn.execute(sql).fetchall()
        logger.info(f'在数据库中找到 {len(l2f_items)} 条记录。')

        l2f_relations = {}
        for l2f_item in l2f_items:
            l2f_relations[l2f_item[0]] = Location2Folder(*l2f_item)
        return l2f_relations

    def convert_db(self, documents: list[WizDocument]):
        """ 将为知笔记中的所有 location 转换成中间格式，等待生成 Joplin Folder
        """
        # 用 location 作为唯一 key
        self.db = {}
        if self.db_file.exists():
            self.db = self.load_from_db()
        for document in documents:
            self.build_location_to_top(document.location, document)

    def update_db(self, location: str, id: str, parent_id: Optional[str] = None):
        """ 更新 Folder 的 guid 到 l2f 对象中
        每次更新都写入 db
        """
        l2f_inst = self.db[location]
        l2f_inst.id = id
        if parent_id is not None:
            l2f_inst.parent_id = parent_id
        self.conn.execute(
            'UPDATE l2f SET parent_id=:parent_id, id=:id WHERE location=:location',
            vars(l2f_inst)
        )
        self.conn.commit()

    def get_waiting_for_created_l2f(self) -> list[Location2Folder]:
        """ 按照 level 排序并返回 l2f 对象，level 低的必须先创建
        """
        waiting_for_created = [v for v in self.db.values() if v.id is None]
        waiting_for_created.sort(key=lambda l2f: l2f.level)
        return waiting_for_created


class Adapter(object):
    """ 负责把为知笔记的对象转换成对应想 Joplin 笔记对象
    """

    ws: WizStorage
    jda: JoplinDataAPI
    work_dir: Path
    l2f: L2FUtil

    folders: dict[str, JoplinFolder]

    def __init__(self, ws: WizStorage, jda: JoplinDataAPI, work_dir: Path=None) -> None:
        self.ws = ws
        self.jda = jda
        self.work_dir = work_dir or default_work_dir

        self.l2f = L2FUtil(self.work_dir.joinpath('w2j.sqlite'))
        # 解析所有的文档
        self.ws.resolve()
        self.l2f.convert_db(self.ws.documents)

    def _upload_folders(self) -> None:
        """ 将为知笔记的目录上传到 Joplin，得到 Folder guid
        """
        waiting_created_l2f = self.l2f.get_waiting_for_created_l2f()
        logger.info(f'有 {len(waiting_created_l2f)} 个 folder 等待创建。')
        for l2f in waiting_created_l2f:
            jf = None
            logger.info(f'开始处理 location {l2f.location}')
            # level1 没有父对象
            if l2f.parent_location is None:
                jf = self.jda.post_folder(title=l2f.title)
                self.l2f.update_db(l2f.location, jf.id)
            else:
                parent_l2f: Location2Folder = self.l2f.db.get(l2f.parent_location)
                if parent_l2f is None:
                    msg = f'找不到父对象 {l2f.parent_location}！'
                    logger.error(msg)
                    raise ValueError(msg)
                if parent_l2f.id is None:
                    msg = f'父对象 {l2f.parent_location} 没有 id！'
                    logger.error(msg)
                    raise ValueError(msg)
                jf = self.jda.post_folder(title=l2f.title, parent_id=parent_l2f.id)
                self.l2f.update_db(l2f.location, jf.id, jf.parent_id)
        self.folders = {}
        for l2f in self.l2f.db.values():
            self.folders[l2f.id] = JoplinFolder(l2f.id, l2f.title, 0, 0, l2f.parent_id)

    def _upload_tag(wiz_tag: WizTag) -> JoplinResource:
        pass

    def _upload_resource(wiz_resource: Union[WizImage, WizAttachment]) -> JoplinResource:
        pass

    def _build_folder():
        pass

    def convert_one(self, wiz_document: WizDocument, folder: Optional[JoplinFolder] = None) -> JoplinNote:
        """ 转换一个为知笔记文档到 Joplin note
        """
        # 没有提供 JoplinFolder 则需要从 location 中生成 JoplinFolder 对象
        if folder is None:
            folder = self._upload_folder(wiz_document.location)

        # 创建一个 joplin note 并将 wiz document 的对应值存入
        note = JoplinNote()
        note.guid = wiz_document.guid
        note.id = tojoplinid(wiz_document.guid)
        note.title = wiz_document.title
        note.folder = folder
        note.source_url = wiz_document.url
        note.created_time = wiz_document.created
        note.updated_time = wiz_document.modified
        note.markup_language = 1 if wiz_document.is_markdown else 2

    def convert_all(self) -> list[JoplinNote]:
        """ 转换一堆为知笔记文档到 Joplin note
        """
        pass

    def resolve(self) -> None:
        pass
