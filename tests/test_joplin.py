from os import name
from pathlib import Path
from w2j.joplin import JoplinDataAPI
import pytest

def test_ping(jda: JoplinDataAPI):
    assert jda.ping()

def test_get_folders(jda: JoplinDataAPI):
    folders, has_more, next_page = jda.get_folders(limit=1)
    assert has_more == True
    # 获取所有的 Folder
    folders, has_more, next_page = jda.get_folders(limit=1, page=0)
    assert has_more == False

@pytest.mark.skip
def test_get_folder(jda: JoplinDataAPI):
    # 临时记录 Folder
    # test_id = 'f02beb3e93f4456ea4032613b9a9575d'
    test_id = '467852588872421b939824efdbc26266'
    folder = jda.get_folder(test_id)
    assert folder.id == test_id

    
@pytest.mark.skip
def test_post_folders(jda: JoplinDataAPI):
    folder = jda.post_folders(title='创新新的folder')
    print(folder)
