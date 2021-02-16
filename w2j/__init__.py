##############################
# w2j =  Wiznote to Joplin
#
# https://github.com/zrong/wiz2joplin
##############################

import logging
import sys

__autho__ = 'zrong'
__version__ = '0.1'

logger = logging.Logger('w2j')
logger.addHandler(logging.StreamHandler(sys.stderr))

from . import wiz
from . import joplin
from . import adapter

__all__ = ['wiz', 'joplin', 'adapter']