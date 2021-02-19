from pathlib import Path
from os import environ

import pytest

from w2j import wiz, joplin
from w2j.adapter import Adapter


@pytest.fixture(scope='session')
def work_dir():
    work_dir = Path(__file__).parent.parent.joinpath('output/')
    if not work_dir.exists():
        work_dir.mkdir()
    return work_dir


@pytest.fixture(scope='session')
def ws(wiz_user_id: str, work_dir: Path):
    """ 提供一个为知笔记存储对象
    """
    wiznote_dir = Path('~/.wiznote').expanduser()
    ws = wiz.WizStorage(wiz_user_id, wiznote_dir, is_group_storage=False, work_dir=work_dir)
    return ws


@pytest.fixture(scope='session')
def wiz_user_id():
    return environ.get('W2J_USER_ID')


@pytest.fixture(scope='session')
def jda():
    return joplin.JoplinDataAPI(
        token='d3098caff3d80561bf915c15cf3f70956c3550fc13e67bee78f74b1a6b2d2632dff10667668cc6682df27d493aa35492b68fa3f642f738fd80547acf571dc17c'
    )

@pytest.fixture(scope='session')
def js():
    joplin_dir = Path('~/.config/joplin-desktop').expanduser()
    return joplin.JoplinStorage(joplin_dir)


@pytest.fixture(scope='session')
def adapter(ws: wiz.WizStorage, jda: joplin.JoplinDataAPI, work_dir: Path):
    return Adapter(ws, jda, work_dir)


@pytest.fixture(scope='session')
def wsg(wiz_user_id: str, work_dir: Path):
    """ 提供一个为知笔记 Group 存储对象
    """
    wiznote_dir = Path('~/.wiznote').expanduser()
    wsg = wiz.WizStorage(wiz_user_id, wiznote_dir, is_group_storage=True, work_dir=work_dir)
    return wsg

@pytest.fixture(scope='session')
def adapter_group(wsg: wiz.WizStorage, jda: joplin.JoplinDataAPI, work_dir: Path):
    return Adapter(wsg, jda, work_dir)