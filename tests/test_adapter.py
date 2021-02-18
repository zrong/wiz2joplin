from w2j.wiz import WizStorage
import pytest

from w2j.adapter import Adapter
from w2j.parser import tojoplinid


@pytest.mark.skip
def test_sync_folders(adapter: Adapter):
    adapter.sync_folders()

@pytest.mark.skip
def test_sync_tags(adapter: Adapter):
    adapter.sync_tags()


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
    wd = ws.build_document(guid)
    jn = adapter._sync_note(wd)
    assert tojoplinid(guid) == jn.id

@pytest.mark.skip
def test_convert_location(ws: WizStorage, adapter: Adapter):
    adapter.sync_note_by_location('/project/k/', True)