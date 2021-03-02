##############################
# w2j =  Wiznote to Joplin
#
# python w2j
# or
# python -m w2j
##############################

import sys
import os

if not __package__:
    path = os.path.join(os.path.dirname(__file__), os.pardir)
    sys.path.insert(0, path)

import w2j
w2j.main()