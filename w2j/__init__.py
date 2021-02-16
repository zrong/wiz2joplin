##############################
# w2j =  Wiznote to Joplin
#
# https://github.com/zrong/wiz2joplin
##############################

import logging
import sys
from pathlib import Path

__autho__ = 'zrong'
__version__ = '0.1'

work_dir = Path(__file__).parent.parent.joinpath('output/')

log_file = work_dir.joinpath('w2j.log')
log_handler = logging.FileHandler(log_file)
log_handler.setFormatter(logging.Formatter('{asctime} - {funcName} - {message}', style='{'))
logger = logging.Logger('w2j')
# logger.addHandler(logging.StreamHandler(sys.stderr))
logger.addHandler(log_handler)

from . import wiz
from . import joplin
from . import adapter

__all__ = ['wiz', 'joplin', 'adapter']