from w2j.wiz_win import WizStorage
from w2j.joplin import JoplinStorage
import pytest

from w2j.adapter import Adapter
from w2j.parser import tojoplinid


@pytest.mark.skip
def test_sync_folders(adapter: Adapter):
    adapter.sync_folders()

@pytest.mark.skip
def test_sync_tags(adapter: Adapter):
    adapter.sync_tags()


@pytest.mark.skip
def test_convert_body(ws: WizStorage, adapter: Adapter):
    """ 测试转换一个文档到 Jopoin
    """
    adapter.sync_folders()
    adapter.sync_tags()
    # 2021-01-4weeks.md
    # guid = '7fdcba42-4d6e-4c1d-a7d8-ffb97a5cca2f'
    # 怎样理性愉快地度过这一生？世界首富巴菲特的合伙人芒格告诉你！
    # guid = 'b500bc97-e6d8-4038-be8d-cd1f182e880c'

    guid = '7594790e-b9ab-463a-bc38-7cc546d76513'
    wd = ws.build_document('01607fd4-2c63-b6a2-0b87-294529a3f645')
    jn = adapter._sync_note(wd)
    assert tojoplinid(guid) == jn.id


def test_convert_location(adapter: Adapter):
    """ 测试转换一个为知笔记目录 到 Joplin，支持同时转换子目录
    """
    location = '/微信收藏/'
    adapter.sync_note_by_location(location, True)


@pytest.mark.skip
def test_convert_all_group(adapter_group: Adapter):
    """ 测试为知笔记的 group 对象
    """
    location = '/collection/技术/'
    adapter_group.sync_all()


@pytest.mark.skip
def test_update_joplin_time(adapter_group: Adapter, js: JoplinStorage):
    times = [
        {'id': tojoplinid(wd.guid), 'created_time': wd.created, 'updated_time': wd.modified or wd.created}
        for wd in adapter_group.ws.documents]
    js.update_time(times)