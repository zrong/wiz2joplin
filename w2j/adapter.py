##############################
# w2j.adapter
#
# 适配器，将解析后的为知笔记对象装备成 joplin 笔记对象
##############################
import sys
from pathlib import Path
from typing import Optional, Union
import json
import sqlite3

from w2j import logger, work_dir as default_work_dir
if sys.platform == "win32":
    from w2j.wiz_win import WizDocument, WizAttachment, WizImage, WizInternalLink, WizTag, WizStorage
else:
    from w2j.wiz_mac import WizDocument, WizAttachment, WizImage, WizInternalLink, WizTag, WizStorage
from w2j.joplin import JoplinNote, JoplinFolder, JoplinResource, JoplinTag, JoplinDataAPI
from w2j.parser import tojoplinid, towizid, convert_joplin_body, JoplinInternalLink


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


class ConvertUtil():
    """ Intermediate process of processing conversion
    """
    # 转换过程中的专用数据库连接
    conn: sqlite3.Connection

    # lzf_db 的内容写入 json 文件中，避免每次都要重新生成 Folder，造成重复
    db_file: Path

    CREATE_SQL: dict[str, str] = {
        # 保存 Location 和 Folder 的关系
        'l2f': """CREATE TABLE l2f (
                location TEXT NOT NULL,
                id TEXT,
                title TEXT NOT NULL,
                parent_location TEXT,
                parent_id TEXT,
                level INTEGER NOT NULL,
                PRIMARY KEY (location)
            );""",
        # The processed documents will be saved here, and the documents that can be found in this table indicate that the conversion has been successful.
        'note': """CREATE TABLE note (
                note_id TEXT not NULL,
                title TEXT not NULL,
                joplin_folder TEXT NOT NULL,
                markup_language INTEGER NOT NULL,
                wiz_location TEXT NOT NULL,
                created_time INTEGER NULL,
                updated_time INTEGER NULL,
                PRIMARY KEY (note_id)
            );""",
        # Processed resources are saved here, including image 和 attachment 资源
        'resource': """CREATE TABLE resource (
                resource_id TEXT not NULL,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_time INTEGER not NULL,
                resource_type INTEGER NOT NULL,
                PRIMARY KEY (resource_id)
            );""",
        # Saved as an internal chain in the knowledge note, that is, resource 与 note 的关系，使用 文档 guid 和 连接目标 guid 同时作为主键。链接目标 guid 为 joplin 格式
        'internal_link': """
            CREATE TABLE internal_link (
                note_id TEXT not NULL,
                resource_id TEXT not NULL,
                title TEXT not NULL,
                link_type TEXT NOT NULL,
                PRIMARY KEY (note_id, resource_id)
            );
            CREATE INDEX idx_link_type ON internal_link (link_type);
            CREATE INDEX idx_resource_id ON internal_link (resource_id);
            """,
        # 保存为知笔记中的 tag
        'tag': """
            CREATE TABLE tag (
                tag_id TEXT not NULL,
                title TEXT not NULL,
                created_time INTEGER not NULL,
                updated_time INTEGER not NULL,
                PRIMARY KEY (tag_id)
            );
            CREATE UNIQUE INDEX idx_title ON tag (title);
        """,
        # 保存tag 与note 的关系
        'note_tag': """CREATE TABLE note_tag (
            note_id TEXT not NULL,
            tag_id TEXT not NULL,
            title TEXT not NULL,
            created_time INTEGER not NULL,
            PRIMARY KEY (note_id, tag_id)
        );""",
    }

    # 目录最大的级别
    folder_max_level: int = 0

    # 将为知笔记转换到 Joplin 目录的结果存储到 dict 中
    l2f_cache: dict[str, Location2Folder]

    folders: dict[str, JoplinFolder]
    tag: dict[str, JoplinTag]
    notes: dict[str, JoplinNote]
    resources: dict[str, JoplinResource]
    internal_links: dict[str, JoplinInternalLink]

    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """ Create database
        """
        self.conn = sqlite3.connect(self.db_file)
        test_table = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?;"

        for table in ('l2f', 'note', 'resource', 'internal_link', 'tag', 'note_tag'):
            table_exists = self.conn.execute(test_table, (table, )).fetchone()[0]
            logger.info(f'table {table} Does it exist: {table_exists}')
            if not table_exists:
                self.conn.executescript(self.CREATE_SQL[table])

    def init_cache(self, documents: list[WizDocument]):
        # 下面的顺序需要严格保持
        # 将 location 转换成 folder
        self.convert_l2f(documents)
        self.load_folders()
        self.load_tags()
        self.load_resources()
        self.load_internal_links()
        self.load_notes()

    def close(self):
        self.conn.close()

    def build_location_to_top(self, location: str, document: Optional[WizDocument] = None):
        """ 构建一个 location 直到最顶端，并返回这个 location 对应的 l2f 对象
        """
        l2f_inst = self.l2f_cache.get(location)
        if l2f_inst is None:
            l2f_inst = Location2Folder(location)
            self.l2f_cache[location] = l2f_inst
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
        if l2f_inst.level > self.folder_max_level:
            self.folder_max_level = l2f_inst.level

    def convert_l2f(self, documents: list[WizDocument]) -> None:
        """ 将为知笔记中的所有 location 转换成中间格式，等待生成 Joplin Folder
        """
        sql = 'SELECT location, title, parent_location, level, id, parent_id FROM l2f;'
        l2f_items = self.conn.execute(sql).fetchall()
        logger.info(f'Found in database l2f {len(l2f_items)} records.')

        # Use location as the only一 key
        self.l2f_cache = {}
        for l2f_item in l2f_items:
            self.l2f_cache[l2f_item[0]] = Location2Folder(*l2f_item)

        for document in documents:
            self.build_location_to_top(document.location, document)

    def get_folder(self, id: str=None, location: str=None) -> JoplinFolder:
        """ 根据 id 或者 location 获取一个 Joplin Folder
        """
        if id:
            return self.folders.get(id)
        elif location:
            l2f = self.l2f_cache.get(location)
            if l2f is not None:
                return self.folders.get(l2f.id)
        return None

    def get_tags(self, guid: str) -> dict[str, JoplinTag]:
        """ 根据 guid 获取该 note 的所有 tag
        """
        sql = 'SELECT tag_id, title FROM note_tag WHERE note_id=?;'
        items = self.conn.execute(sql, (guid, )).fetchall()
        logger.info(f'In the database note_tag Found in note {guid} of {len(items)} strip tag records.')
        tag_dict: dict[str, JoplinTag] = {}
        for item in items:
            tag_id = item[1]
            tag_dict[tag_id] = self.tags[tag_id]
        return tag_dict

    def get_resources(self, links: dict[str, JoplinInternalLink]) -> dict[str, JoplinResource]:
        """ 根据内链获取对应的 resource
        """
        resource_dict: dict[str, JoplinResource] = {}
        for jil in links.values():
            resource = self.resources.get(jil.resource_id)
            if resource:
                resource_dict[jil.resource_id] = resource
        return resource_dict

    def get_internal_links(self, guid: str) -> dict[str, JoplinInternalLink]:
        sql = 'SELECT note_id, resource_id, title, link_type FROM internal_link WHERE note_id=?;'
        items = self.conn.execute(sql, (guid, )).fetchall()
        logger.info(f'In the database internal_link found in note {guid} of {len(items)} internal chain records.')
        links = {}
        for item in items:
            # 优先从缓存中获取 jil 对象
            id = f'{item[0]}-{item[1]}'
            jil: JoplinInternalLink = self.internal_links.get(id, JoplinInternalLink(*item))
            links[id] = jil
        return links

    def get_note(self, note_id: str) -> JoplinNote:
        return self.notes.get(note_id)

    def load_folders(self) -> None:
        """ 将数据库中的 JoplinFolder 载入
        数据库中保存的是  Location2Folder 对象，将其转换成 JoplinFolder
        """
        self.folders = {}
        for l2f in self.l2f_cache.values():
            self.folders[l2f.id] = JoplinFolder(l2f.id, l2f.title, 0, 0, l2f.parent_id)

    def load_tags(self) -> None:
        """ 从数据库中载入已经创建的 tag 信息
        """
        sql = 'SELECT tag_id, title, created_time, updated_time FROM tag;'
        tag_items = self.conn.execute(sql).fetchall()
        logger.info(f'In the database tag found {len(tag_items)} records.')
        self.tags = {}
        for tag_item in tag_items:
            self.tags[tag_item[0]] = JoplinTag(*tag_item)

    def load_resources(self) -> None:
        sql = 'SELECT resource_id, title, filename, created_time, resource_type FROM resource;'
        items = self.conn.execute(sql).fetchall()
        logger.info(f'In the database resource found {len(items)} records.')
        self.resources = {}
        for item in items:
            jr = JoplinResource(*item)
            self.resources[jr.id] = jr

    def load_notes(self) -> None:
        """ Load the synchronized from the database note
        """
        sql = 'SELECT note_id, title, joplin_folder, markup_language, wiz_location, created_time, updated_time FROM note;'
        items = self.conn.execute(sql).fetchall()
        logger.info(f'In the database note found {len(items)} records.')
        self.notes = {}
        for item in items:
            jn = JoplinNote(item[0], item[1], item[2], item[3], location=item[4], created_time=item[5], updated_time=item[6])
            jn.folder = self.folders[jn.parent_id]
            jn.internal_links = self.get_internal_links(jn.id)
            jn.resources = self.get_resources(jn.internal_links)
            jn.tags = self.get_tags(jn.id)
            self.notes[jn.id] = jn

    def load_internal_links(self) -> None:
        sql = 'SELECT note_id, resource_id, title, link_type FROM internal_link;'
        items = self.conn.execute(sql).fetchall()
        logger.info(f'In the database internal_link found {len(items)} internal chain records.')
        self.internal_links = {}
        for item in items:
            jil: JoplinInternalLink = JoplinInternalLink(*item)
            self.internal_links[jil.id] = jil

    def add_tag(self, tag: JoplinTag) -> None:
        """ 向数据库中加入一个没有创建过的 tag
        """
        if self.tags.get(tag.id) is not None:
            logger.warning(f'tag {tag.id} |{tag.title}| already exists and does not need to be added.')
            return
        sql = 'INSERT INTO tag (tag_id, title, created_time, updated_time) VALUES (?, ?, ?, ?);'
        self.conn.execute(sql, (tag.id, tag.title, tag.created_time, tag.updated_time))
        self.tags[tag.id] = tag
        self.conn.commit()

    def add_resource(self, jr: JoplinResource) -> None:
        """ 向数据库中加入一个没有创建过的 resource
        """
        if self.resources.get(jr.id) is not None:
            logger.warning(f'resource {jr.id} |{jr.title}| already exists and does not need to be added.')
            return
        sql = 'INSERT INTO resource (resource_id, title, filename, created_time, resource_type) VALUES (?, ?, ?, ?, ?);'
        self.conn.execute(sql, (jr.id, jr.title, jr.filename, jr.created_time, jr.resource_type))
        self.resources[jr.id] = jr
        self.conn.commit()

    def add_internal_lnk(self, jil: JoplinInternalLink) -> None:
        if self.internal_links.get(jil.id) is not None:
            logger.warning(f'internal_link {jil.id} |{jil.title}-{jil.link_type}| already exists in the database and does not need to be added.')
            return
        sql = 'INSERT INTO internal_link (note_id, resource_id, title, link_type) VALUES (?, ?, ?, ?);'
        self.conn.execute(sql, (jil.note_id, jil.resource_id, jil.title, jil.link_type))
        self.internal_links[jil.id] = jil
        self.conn.commit()

    def add_note_tag(self, note: JoplinNote, tag: JoplinTag) -> None:
        """ Add one note tag
        """
        test_note_tag = "SELECT count(*) FROM note_tag WHERE note_id=? AND tag_id=?;"
        note_tag_item = self.conn.execute(test_note_tag, (note.id, tag.id)).fetchone()
        if note_tag_item:
            logger.warning(f'note {note.id}|{note.title}| of tag {tag.id}|{tag.title}| already exists！')
            return
        sql = 'INSERT INTO note_tag (note_id, tag_id, title, created_time) VALUES (?, ?, ?, ?);'
        self.conn.execute(sql, (note.id, tag.id, tag.title, tag.created_time))
        self.conn.commit()

    def add_note(self, note: JoplinNote) -> None:
        if self.notes.get(note.id) is not None:
            logger.warning(f'note {note.id} |{note.title}| already exists in the database and does not need to be added.')
            return
        sql = 'INSERT INTO note (note_id, title, joplin_folder, markup_language, wiz_location, created_time, updated_time) VALUES (?, ?, ?, ?, ?, ?, ?);'
        self.conn.execute(sql, (note.id, note.title, note.parent_id, note.markup_language, note.location, note.created_time, note.updated_time))
        self.conn.commit()

        self.notes[note.id] = note
        for tag in note.tags.values():
            self.add_note_tag(note, tag)
        for jil in note.internal_links.values():
            self.add_internal_lnk(jil)

    def update_l2f(self, location: str, id: str, parent_id: Optional[str] = None):
        """ update Folder 的 guid 到 l2f 对象中
        每次更新都写入 db
        """
        l2f_inst = self.l2f_cache[location]
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
        waiting_for_created = [v for v in self.l2f_cache.values() if v.id is None]
        waiting_for_created.sort(key=lambda l2f: l2f.level)
        return waiting_for_created


class Adapter(object):
    """ 负责把为知笔记的对象转换成对应想 Joplin 笔记对象
    """

    ws: WizStorage
    jda: JoplinDataAPI
    work_dir: Path
    cu: ConvertUtil

    def __init__(self, ws: WizStorage, jda: JoplinDataAPI, work_dir: Path=None) -> None:
        self.ws = ws
        self.jda = jda
        self.work_dir = work_dir or default_work_dir

        # Parse all documents
        self.ws.resolve()

        # Load cache from database
        self.cu = ConvertUtil(self.work_dir.joinpath('w2j.sqlite'))
        self.cu.init_cache(self.ws.documents)

    def sync_folders(self) -> None:
        """ Synchronize the directory of WizNote to Joplin Folder
        In WizNote, the directory is not a resource, it is directly defined in the configuration file, and it is only used as a resource in the database. location Field exists
        and in Joplin the directory is a standard resource https://joplinapp.org/api/references/rest_api/#item-type-ids
        """
        waiting_created_l2f = self.cu.get_waiting_for_created_l2f()
        logger.info(f'have {len(waiting_created_l2f)} a folder wait for synchronization.')
        for l2f in waiting_created_l2f:
            jf = None
            logger.info(f'Deal with location {l2f.location}')
            # level1 (No parent object)
            if l2f.parent_location is None:
                jf = self.jda.post_folder(title=l2f.title)
                self.cu.update_l2f(l2f.location, jf.id)
            else:
                parent_l2f: Location2Folder = self.cu.l2f_cache.get(l2f.parent_location)
                if parent_l2f is None:
                    msg = f'Parent object not found {l2f.parent_location}！'
                    logger.error(msg)
                    raise ValueError(msg)
                if parent_l2f.id is None:
                    msg = f'Parent object {l2f.parent_location} no id！'
                    logger.error(msg)
                    raise ValueError(msg)
                jf = self.jda.post_folder(title=l2f.title, parent_id=parent_l2f.id)
                self.cu.update_l2f(l2f.location, jf.id, jf.parent_id)
        # updated l2f_cache after that, update it once folders
        self.cu.load_folders()

    def sync_tags(self) -> None:
        """ Synchronization of notes for knowledge tag to Joplin Tag
        """
        created_keys = self.cu.tags.keys()
        waiting_create_tags = [wt for wt in self.ws.tags if not tojoplinid(wt.guid) in created_keys]
        logger.info(f'Total number of notes tags: {len(self.ws.tags)}')
        logger.info(f'have {len(waiting_create_tags)} tag wait for synchronization.')
        for wt in waiting_create_tags:
            tag_id = tojoplinid(wt.guid)
            try:
                logger.info(f'Deal with tag {wt.name} {tag_id}')
                jt = self.jda.post_tag(id=tag_id, title=wt.name, created_time=wt.modified, updated_time=wt.modified)
                self.cu.add_tag(jt)
            except ValueError as e:
                logger.error(e)
                # 由于加入的 tag 没有写入转换数据库导致的 guid 重复错误，此时需要将 tag 写入转换数据库
                if str(e).find('SQLITE_CONSTRAINT: UNIQUE constraint failed') > -1:
                    jt = self.jda.get_tag(tag_id)
                    self.cu.add_tag(jt)
                continue

    def _upload_wiz_attachment(self, attach: WizAttachment) -> JoplinResource:
        """ Upload an unknown attachment
        """
        resource_id = tojoplinid(attach.guid)
        jr: JoplinResource = self.cu.resources.get(resource_id)
        if jr is not None:
            logger.warning(f'resource {resource_id} |{jr.title}| already exists!')
            return jr
        jr = self.jda.post_resource(
            attach.file,
            1,
            id=tojoplinid(attach.guid),
            title=attach.name,
            filename=attach.name,
            created_time=attach.modified,
            updated_time=attach.modified
        )
        self.cu.add_resource(jr)
        return jr

    def _upload_wiz_image(self, image: WizImage) -> JoplinResource:
        """ Upload a known image
        """
        jr: JoplinResource = self.jda.post_resource(
            image.file,
            2,
            title=image.src,
            filename=image.src
        )
        self.cu.add_resource(jr)
        return jr

    def _sync_note(self, document: WizDocument) -> JoplinNote:
        """ Sync a note
        """
        logger.info(f'Processing document {document.guid}|{document.title}|。')
        note_id = tojoplinid(document.guid)
        jn: JoplinNote = self.cu.get_note(note_id)
        if jn is not None:
            logger.warning(f'note {jn.id} |{jn.title}| already exists！')
            return

        # 临时保存上传成功后生成的 Image 和 Attachment 对应的 Joplin Resource
        resources_in_note: dict[str, JoplinResource] = {}

        # 为知笔记中的图像不在内链中，附件也可能不在内链中，将它们全部加入内链。
        # 附件即使已经包含在内链中了，也需要在 body 末尾再加上一个内链
        joplin_internal_links: dict[str, JoplinInternalLink] = {}

        # 处理为知笔记文档中已经包含的内链
        for wil in document.internal_links:
            resource_id = tojoplinid(wil.guid)
            jil: JoplinInternalLink = JoplinInternalLink(note_id, resource_id,  wil.title, wil.link_type, wil.outerhtml)
            joplin_internal_links[jil.id] = jil

        # 上传附件
        for attachment in document.attachments:
            # 不是知道这个":"用法,是不是良好习惯，一直以为只能用在func定义返回类型
            jr: JoplinResource = self._upload_wiz_attachment(attachment)
            resources_in_note[jr.id] = jr

            jil_id = f'{note_id}-{jr.id}'
            jil: JoplinInternalLink = joplin_internal_links.get(jil_id)
            if jil is not None:
                logger.warning(f'Internal link {jil_id} already exists！')
                continue

            # This attachment exists in the attachment list, but in body Does not exist, not at this time outerhtml，You need to add this attachment to when converting body end
            jil: JoplinInternalLink = JoplinInternalLink(note_id, jr.id, jr.title, 'open_attachment')
            joplin_internal_links[jil.id] = jil

        # 上传图像，将每个文档中的图像生成为 Jopin 中的资源
        for image in document.images:
            jr: JoplinResource = self._upload_wiz_image(image)
            resources_in_note[jr.id] = jr
            jil: JoplinInternalLink = JoplinInternalLink(note_id, jr.id, jr.title, 'image', image.outerhtml)
            joplin_internal_links[jil.id] = jil

        # 创建一个 joplin note 并将 wiz document 的对应值存入
        body = convert_joplin_body(
            document.body,
            document.is_markdown,
            joplin_internal_links.values()
           )

        folder = self.cu.get_folder(location=document.location)
        note: JoplinNote = self.jda.post_note(note_id, document.title, body, document.is_markdown, folder.id, document.url, document.created, document.modified)
        note.internal_links = joplin_internal_links
        note.folder = folder
        note.tags = self.cu.get_tags(note.id)
        self.cu.add_note(note)

        return note
        
    def _get_locations(self, location: str, locations: list[str]) -> None:
        """ Get one location from all location
        """
        cur_l2f = self.cu.l2f_cache.get(location)
        if cur_l2f is None:
            raise ValueError(f'Can not find {location}')
        for l2f in self.cu.l2f_cache.values():
            if l2f.parent_location and l2f.level > cur_l2f.level and l2f.parent_location == location:
                # print(f'{cur_l2f.level} {l2f.level} {self.cu.folder_max_level} {l2f.parent_location} {l2f.location} {location}')
                locations.append(l2f.location)
                self._get_locations(l2f.location, locations)

    def sync_note_by_location(self, location: str, with_children: bool=True) -> None:
        """ Synchronize all notes in the directory
        """
        self.sync_folders()
        self.sync_tags()
        locations = [location]
        if with_children:
            self._get_locations(location, locations)
        logger.info(f'Deal with the following location： {locations}')
        waiting_for_sync = [wd for wd in self.ws.documents if wd.location in locations]
        logger.info(f'List of Notes for Knowledge {location} Among them are {len(waiting_for_sync)} the notes are waiting to be synchronized.')
        for wd in waiting_for_sync:
            self._sync_note(wd)

    def sync_all(self) -> None:
        """ Sync all content
        """
        self.sync_folders()
        self.sync_tags()
        logger.info(f'Convert all documents for knowing notes {len(self.ws.documents)} article.')
        for wd in self.ws.documents:
            self._sync_note(wd)
