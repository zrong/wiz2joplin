##############################
# w2j.adapter
#
# 适配器，将解析后的为知笔记对象装备成 joplin 笔记对象
##############################

from os import PathLike
from pathlib import Path
from typing import Optional, Union
import json

from w2j.wiz import WizDocument, WizAttachment, WizImage, WizInternalLink, WizTag, WizStorage
from w2j.joplin import JoplinNote, JoplinFolder, JoplinResource, JoplinTag, JoplinDataAPI
from w2j.parser import tojoplinid


class Location2Folder(object):
    """ 为知笔记的 Location 与 Joplin 的 Folder 之转换关系
    """
    # Joplin Folder guid，只有创建之后才会存在
    id: str

    # 当前目录的名称
    title: str

    # 为知笔记的全路径名称（包含 / 的所有部分）
    location: str

    # 为知笔记的父全路径名称
    parent_location: str

    # 父 Joplin Folder guid
    parent_id: str

    def __init__(self, location: str, id: str = None, parent_id: str = None) -> None:
        self.location = location

        # 去掉头尾的 / 后使用 / 分隔
        titles = location[1:-1].split('/')
        # 最后一个是当前目录
        self.title = titles[-1]
        # 有父目录
        if len(titles) > 1:
            self.parent_location = '/' + '/'.join(titles[:-2]) + '/'
        else:
            self.parent_location = None

        self.id = id
        self.parent_id = parent_id

    @classmethod
    def load_from_db(cls, db: Path):
        l2f_conf: dict[str, dict] = json.load(db)
        l2f_relations = {}
        for location, l2f_obj in l2f_conf.items():
            l2f_relations[location] = cls(l2f_obj['location'], l2f_obj['id'], l2f_obj['parent_id'])
        # 合并 parent 关系
        for location, l2f_instance in l2f_relations.items():
            # if l2f_instance.parent
            if l2f_instance.parent_id:
                l2f_instance.parent = l2f_relations.get(l2f_instance)
        return l2f_relations

    @classmethod
    def build_location_to_top(cls, location: str, l2f_relations: dict):
        """ 构建一个 location 直到最顶端，并返回这个 location 对应的 l2f 对象
        """
        l2f_inst = l2f_relations.get(location)
        if l2f_inst is None:
            l2f_inst = cls(location)
            l2f_relations[location] = l2f_inst
        if l2f_inst is not None and l2f_inst.parent_location is not None:
            cls.build_location_to_top(l2f_inst.parent_location, l2f_relations)
        return l2f_inst

    def __repr__(self) -> str:
        return f'<Location2Folder id: {self.id}, title: {self.title}, location: {self.location}, parent_id: {self.parent_id}>'


class Adapter(object):
    """ 负责把为知笔记的对象转换成对应想 Joplin 笔记对象
    """

    ws: WizStorage
    jda: JoplinDataAPI
    work_dir: Path

    # 将为知笔记转换到 Joplin 目录的结果存储到 dict 中
    l2f_db: dict
    # lzf_db 的内容写入 json 文件中，避免每次都要重新生成 Folder，造成重复
    l2f_db_file: Path

    def __init__(self, ws: WizStorage, jda: JoplinDataAPI, work_dir: Path) -> None:
        self.ws = ws
        self.jda = jda
        self.work_dir = work_dir

        self.l2f_db = work_dir.joinpath('location_to_folder.json')
        # 解析所有的文档
        self.ws.resolve()
        self._convert_location_to_folder()
        self._save_l2f_db()

    def _convert_location_to_folder(self):
        """ 将为知笔记中的所有 location 转换成中间格式，等待生成 Joplin Folder
        """
        # 用 location 作为唯一 key
        l2f_with_location = {}
        if self.l2f_db_file.exists():
            l2f_with_location = Location2Folder.load_from_db(self.l2f_db_file)
        for document in self.ws.documents:
            l2f_inst = Location2Folder.build_location_to_top(document.location, l2f_with_location)
            document.folder = l2f_inst

    def _save_l2f_db(self):
        """ 保存 l2f_db 到 l2f_db_file
        """
        json.dump(self.l2f_db, self.l2f_db_file, default=lambda l2f: vars(l2f))

    def _upload_folder(self, wiz_location: str) -> JoplinFolder:
        """ 转换为知笔记的目录到 Joplin Folder
        """
        pass

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
