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
    wiznote_dir = Path('~/.wiznote').expanduser()
    ws = wiz.WizStorage(wiz_user_id, wiznote_dir, is_group_storage=False, work_dir=work_dir)
    return ws


@pytest.fixture(scope='session')
def wiz_user_id():
    return environ.get('W2J_USER_ID')


@pytest.fixture(scope='session')
def jda():
    return joplin.JoplinDataAPI(
        token='90284420dc2db743d6ac1b803346c7330fdbf5d1f6a26a10f42dee448a7d35895b470bcffcb0061d90a742e513a33d7dd6b858c7ebfc89538fab0e69e682aa21'
    )


@pytest.fixture(scope='session')
def adapter(ws: wiz.WizStorage, jda: joplin.JoplinDataAPI, work_dir: Path):
    return Adapter(ws, jda, work_dir)