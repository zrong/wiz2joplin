import pytest

from w2j.adapter import Adapter


@pytest.mark.skip
def test_save_l2f_db(adapter: Adapter):
    """ 测试保存 l2f.json
    """
    adapter._upload_folders()

def test_create_sqlite(adapter: Adapter):
    cursor = adapter.l2f.conn.executemany(
        'INSERT INTO l2f(location, title, parent_location, level, id, parent_id) VALUES (:location, :title, :parent_location, :level, :id, :parent_id)',
        [vars(l2f) for l2f in adapter.l2f.db.values()]
    )
    adapter.l2f.conn.commit()
    adapter.l2f.close()
    print(cursor.rowcount)
