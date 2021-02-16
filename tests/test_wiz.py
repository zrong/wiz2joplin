from w2j.wiz import WizStorage
from pathlib import Path
import pytest


def test_datadir(wiz_user_id: str, ws: WizStorage):
    wiznote_dir = Path('~/.wiznote').expanduser()
    assert str(ws.data_dir.data_dir.resolve()) == str(wiznote_dir.joinpath(wiz_user_id).joinpath('data').resolve())


@pytest.mark.skip
def test_build_tags(ws: WizStorage):
    """ 测试 tag
    """
    tags, tags_dict = ws._build_tags()
    assert len(tags_dict.keys()) > 0


@pytest.mark.skip
def test_build_attachments(ws: WizStorage):
    """ 测试附件
    """
    attachments, attachments_in_document = ws._build_attachments()
    # 附件总量一般会大于包含附件文档的数量，因为许多文档包含不止一个附件
    assert len(attachments) > len(attachments_in_document)
    

@pytest.mark.skip
def test_build_documents(ws: WizStorage):
    """ 测试文档
    """
    documents = ws.build_documents()
    document_rows = ws.data_dir._get_all_document()
    assert len(documents) == len(document_rows)


@pytest.mark.skip
def test_build_document(ws: WizStorage):
    """ 测试获取一个文档
    """
    # 没有 attachment，有一个 tag
    one_tag = '49c21d80-dc3f-47d6-b37b-7b5602133600'

    # Flash向量-8-球和角，有一个 attachment
    two_open_attachment = '44fba993-8f62-4eef-a7db-5f8b332d95d3'

    # 2021-02-1weeks.md
    four_open_document = '32321691-f842-4cf2-8a1a-e9f3f1212a42'

    # linux 技巧：使用 screen 管理你的远程会话
    more_images = 'f38c347c-17cb-4342-a063-861876f70660'

    # 超过 10 个图像
    more_images2 = 'cc18a030-7445-43ad-939a-ad9e264da8d7'
    document = ws.build_document(more_images)

    # document = ws.build_document(four_open_document)
    assert document.title == 'Flash向量-8-球和角'