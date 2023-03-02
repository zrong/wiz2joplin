Migrate from WizNote to Joplin.

## !!!CAUTION!!!!

wiz2joplin 0.5 has only been tested in wizNote for Win with wiznote ver4.13.25, not test in wiznoteX.

The folder structure of the macOS and Windows versions of wizNote is different, but maybe this version is also compatible for mac.

All log messages and error messages translate to english only for windows wersion.

This version migrate DateCreated and DateModified of notes.

Struct of folder on Win:
```
<some path> example D:
  wiz2joplin
    wiz
      user@mail.com - Fully copied data directory (ex: C:\Users\user\Documents\My Knowledge\Data\user@mail.com
    out - empty folder
    w2j - updated script files (from this fork)
```
## Dependency

- Python 3.9
- macOS Catalina or above
- wizNote for Mac 2.8.7 (2020.8.20 10:28)
- ![wiznote for macOS](wiznoteformac.png)

## Installation

To install this tool, you can use pip:

```
python -m venv ~/w2j/venv
~/w2j/venv/bin/activate
pip install w2j
```

Alternatively, you can install the package using the bundled setup script:

```
python -m venv ~/w2j/venv
source ~/w2j/venv/bin/activate
python setup.py install
```

## Usage

If your WizNote user id is `youremail@yourdomain.com`, the token in Joplin Web Clipper is `aa630825022a340ecbe5d3e2f25e5f6a`, and Joplin run on the same computer, you can use wiz2joplin like follows.

Convert all of documents from wizNote to Joplin:

``` shell
cd w2j
python __main__.py -o D:\w2j\out -w D:\w2j\wiz -u user@mail.ru -t df9785823ce435759291943653c299873a13c29493a631aa5bc8c37d95749912d931a55d8e01beeb0347a86f4f1bc918c2f2a3899a863d5d8190af0482dd2d65 -a
```

```

Use `w2j --help` to show usage for w2j:

```
```
usage: w2j [-h] --output OUTPUT --wiz-dir WIZNOTE_DIR --wiz-user
           WIZNOTE_USER_ID --joplin-token JOPLIN_TOKEN
           [--joplin-host JOPLIN_HOST] [--joplin-port JOPLIN_PORT]
           [--location LOCATION] [--location-children] [--all][--log-level]

Migrate from WizNote to Joplin.

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        The output dir for unziped WizNote file and log file.
                        e.g. ~/wiz2joplin_output or
                        C:\Users\zrong\wiz2joplin_output
  --wiz-dir WIZNOTE_DIR, -w WIZNOTE_DIR
                        Set the data dir of WizNote. e.g ~/.wiznote or
                        C:\Program Files\WizNote
  --wiz-user WIZNOTE_USER_ID, -u WIZNOTE_USER_ID
                        Set your user id(login email) of WizNote.
  --joplin-token JOPLIN_TOKEN, -t JOPLIN_TOKEN
                        Set the authorization token to access Joplin Web
                        Clipper Service.
  --joplin-host JOPLIN_HOST, -n JOPLIN_HOST
                        Set the host of your Joplin Web Clipper Service,
                        default is 127.0.0.1
  --joplin-port JOPLIN_PORT, -p JOPLIN_PORT
                        Set the port of your Joplin Web Clipper Service,
                        default is 41184
  --location LOCATION, -l LOCATION
                        Convert the location of WizNote, e.g. /My Notes/. If
                        you use the --all parameter, then skip --location
                        parameter.
  --location-children, -r
                        Use with --location parameter, convert all children
                        location of --location.
  --all, -a             Convert all documents of your WizNote.
  --log-level           Use with --log-level to set the log level, default is INFO,
                        other choice are "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG".
```

## Log file

Please read log file `w2j.log` under --output directory to check the conversion states.

## Source code analysis related articles

- [from WizNote to the notes of Joplin（1）](https://blog.zengrong.net/post/wiznote2joplin1/)
- [from WizNote to the notes of Joplin（2）](https://blog.zengrong.net/post/wiznote2joplin2/)
- [WizNote on macOS Local folder analysis](https://blog.zengrong.net/post/analysis-of-wiznote/)
- [Use Tencent Cloud Object Storage (COS) to achieve Joplin synchronization](https://blog.zengrong.net/post/joplin-sync-use-cos/)
- [configuration Joplin Server Achieve synchronization](https://blog.zengrong.net/post/joplin-server-config/)
