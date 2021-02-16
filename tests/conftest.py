from w2j.joplin import JoplinDataAPI
from w2j import wiz
from pathlib import Path
from os import environ
import pytest


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
    return JoplinDataAPI()