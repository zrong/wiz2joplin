from w2j.wiz import WizStorage
from pathlib import Path


def test_datadir(wiz_user_id: str, ws: WizStorage):
    wiznote_dir = Path('~/.wiznote').expanduser()
    assert str(ws.data_dir.data_dir.resolve()) == str(wiznote_dir.joinpath(wiz_user_id).joinpath('data').resolve())

def test_build_tags(ws: WizStorage):
    """ 测试 tag
    """
    tags, tags_dict = ws._build_tags()
    assert len(tags_dict.keys()) > 0

def test_build_attachments(ws: WizStorage):
    """ 测试附件
    """
    attachments, attachments_in_document = ws._build_attachments()
    # 附件总量一般会大于包含附件文档的数量，因为许多文档包含不止一个附件
    assert len(attachments) > len(attachments_in_document)
    
def test_build_documents(ws: WizStorage):
    """ 测试文档
    """
    documents = ws.build_documents()
    # print(len(documents))