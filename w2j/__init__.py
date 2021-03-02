##############################
# w2j =  Wiznote to Joplin
#
# https://github.com/zrong/wiz2joplin
##############################

import logging
import sys
from pathlib import Path
import argparse

__autho__ = 'zrong'
__version__ = '0.4'

work_dir = Path.cwd()
logger = logging.Logger('w2j')
log_file = work_dir.joinpath('w2j.log')
log_handler = logging.FileHandler(log_file)
log_handler.setFormatter(logging.Formatter('{asctime} - {funcName} - {message}', style='{'))
# logger.addHandler(logging.StreamHandler(sys.stderr))
logger.addHandler(log_handler)


parser = argparse.ArgumentParser('w2j', description='Migrate from WizNote to Joplin.')
parser.add_argument('--output', '-o', type=str, metavar='OUTPUT', required=True, help='The output dir for unziped WizNote file and log file. e.g. ~/wiz2joplin_output or C:\\Users\\zrong\\wiz2joplin_output')
parser.add_argument('--wiz-dir', '-w', type=str, metavar='WIZNOTE_DIR', required=True, help='Set the data dir of WizNote. e.g ~/.wiznote or C:\\Program Files\\WizNote')
parser.add_argument('--wiz-user', '-u', type=str, metavar='WIZNOTE_USER_ID', required=True, help='Set your user id(login email) of WizNote.')
parser.add_argument('--joplin-token', '-t', type=str, metavar='JOPLIN_TOKEN', required=True, help='Set the authorization token to access Joplin Web Clipper Service.')
parser.add_argument('--joplin-host', '-n', type=str, metavar='JOPLIN_HOST', default='127.0.0.1', help='Set the host of your Joplin Web Clipper Service, default is 127.0.0.1')
parser.add_argument('--joplin-port', '-p', type=int, metavar='JOPLIN_PORT', default=41184, help='Set the port of your Joplin Web Clipper Service, default is 41184')
parser.add_argument('--location', '-l', type=str, metavar='LOCATION', help='Convert the location of WizNote, e.g. /My Notes/. If you use the --all parameter, then skip --location parameter.')
parser.add_argument('--location-children', '-r', action='store_true', help='Use with --location parameter, convert all children location of --location.')
parser.add_argument('--all', '-a', action='store_true', help='Convert all documents of your WizNote.')
args = parser.parse_args()


from . import wiz
from . import joplin
from . import adapter

__all__ = ['wiz', 'joplin', 'adapter']


def main() -> None:
    if args.location is None and args.all == False:
        print('Please set --location to assign the location of WizNote, or use --all to convert all of the documents!')
        return
    wiznote_dir = Path(args.wiz_dir).expanduser()
    if not wiznote_dir.exists():
        print(f'The wiznote directory {wiznote_dir} is not exists!')
        return
    output_dir = Path(args.output).expanduser()
    if not output_dir.exists():
        output_dir.mkdir()
    logger.removeHandler(log_file)
    newlog_file = output_dir.joinpath('w2j.log')
    print(f'Please read [{newlog_file.resolve()}] to check the conversion states.')
    logger.addHandler(logging.FileHandler(newlog_file))
    jda = joplin.JoplinDataAPI(
        host=args.joplin_host,
        port=args.joplin_port,
        token=args.joplin_token
    )
    ws = wiz.WizStorage(args.wiz_user, wiznote_dir, is_group_storage=False, work_dir=output_dir)
    ad = adapter.Adapter(ws, jda, work_dir=output_dir)
    if args.all:
        ad.sync_all()
    else:
        ad.sync_note_by_location(args.location, args.location_children)
