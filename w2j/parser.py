##############################
# w2j.parser
# 解析器，解析 html 源码
##############################

from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
import chardet


RE_A_START = r'<a href="'
RE_A_END = r'">([^<]+)</a>'

# 早期的连接没有双斜杠
# wiz:open_attachment?guid=8337764c-f89d-4267-bdf2-2e26ff156098
# wiz://open_attachment?guid=52935f17-c1bb-45b7-b443-b7ba1b6f854e
# 
RE_OPEN_ATTACHMENT_HREF = r'wiz:/{0,2}(open_\w+)\?guid=([a-z0-9\-]{36})'
RE_OPEN_ATTACHMENT_OUTERHTML = RE_A_START + RE_OPEN_ATTACHMENT_HREF + RE_A_END


# wiz://open_document?guid=c6204f26-f966-4626-ad41-1b5fbdb6829e&amp;kbguid=&amp;private_kbguid=69899a48-dc52-11e0-892c-00237def97cc
RE_OPEN_DOCUMENT_HREF = r'wiz:/{0,2}(open_\w+)\?guid=([a-z0-9\-]{36})&amp;kbguid=&amp;private_kbguid=([a-z0-9\-]{36})'
RE_OPEN_DOCUMENT_OUTERHTML = RE_A_START + RE_OPEN_DOCUMENT_HREF + RE_A_END


# 图像文件在 body 中存在的形式，即使是在 .md 文件中，也依然使用这种形式存在
RE_IMAGE_OUTERHTML = r'<img .*?src="(index_files/[^"]+)"[^>]*>'


def parse_wiz_html(index_html: Path, title: str) -> tuple[str, list[re.Match], list[re.Match]]:
    """ 在为知笔记文档的 index.html 中搜索内链的附件和文档链接
    """
    html_body_bytes = index_html.read_bytes()
    # 早期版本的 html 文件使用的是 UTF-16 LE(BOM) 编码保存。最新的文件是使用 UTF-8(BOM) 编码保存。要判断编码进行解析
    enc = chardet.detect(html_body_bytes)
    html_body = html_body_bytes.decode(encoding=enc['encoding'])

    # 去掉换行符，早期版本的 html 文件使用了 \r\n 换行符，而且会切断 html 标记。替换掉换行符方便正则
    html_body = html_body.replace('\r\n', '')
    html_body = html_body.replace('\n', '')

    open_attachments = re.finditer(RE_OPEN_ATTACHMENT_OUTERHTML, html_body, re.IGNORECASE)
    open_documents = re.finditer(RE_OPEN_DOCUMENT_OUTERHTML, html_body, re.IGNORECASE)
    return html_body, open_attachments, open_documents


def parse_wiz_image(html_body: str) -> list[re.Match]:
    """ 在为知笔记 html 源码中搜索图像
    """
    return re.finditer(RE_IMAGE_OUTERHTML, html_body, re.IGNORECASE)


def tots(dt: str):
    """ 转换本地时间到时间戳，数据库中记录的是东八区本地时间
    """
    return int(datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=8))).timestamp()*1000)


def towizid(id: str) -> str:
    """ 从 joplin 的 id 格式转为 wiz 的 guid 格式
    """
    one = id[:8]
    two = id[8:12]
    three = id[12:16]
    four = id[16:20]
    five = id[20:]
    return '-'.join([one, two, three, four, five])


def tojoplinid(guid: str) -> str:
    """ 从 wiz 的 guid 格式转为 joplin 的 id 格式
    """
    return ''.join(guid.split('-'))