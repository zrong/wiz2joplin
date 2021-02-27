##############################
# w2j.parser
# 解析器，解析 html 源码
##############################

from datetime import datetime, timezone, timedelta
from os import link
from pathlib import Path
import re
import chardet
from inscriptis import get_text


RE_A_START = r'<a href="'
RE_A_END = r'">([^<]+)</a>'

# 附件内链
# 早期的链接没有双斜杠
# wiz:open_attachment?guid=8337764c-f89d-4267-bdf2-2e26ff156098
# 后期的链接有双斜杠
# wiz://open_attachment?guid=52935f17-c1bb-45b7-b443-b7ba1b6f854e
RE_OPEN_ATTACHMENT_HREF = r'wiz:/{0,2}(open_\w+)\?guid=([a-z0-9\-]{36})'
RE_OPEN_ATTACHMENT_OUTERHTML = RE_A_START + RE_OPEN_ATTACHMENT_HREF + RE_A_END

# 文档内链，只需要提取 guid 后面的部分即可
# wiz://open_document?guid=c6204f26-f966-4626-ad41-1b5fbdb6829e&amp;kbguid=&amp;private_kbguid=69899a48-dc52-11e0-892c-00237def97cc
RE_OPEN_DOCUMENT_HREF = r'wiz:/{0,2}(open_\w+)\?guid=([a-z0-9\-]{36})&amp;kbguid=&amp;private_kbguid=([a-z0-9\-]{36})'
RE_OPEN_DOCUMENT_OUTERHTML = RE_A_START + RE_OPEN_DOCUMENT_HREF + RE_A_END


# 图像文件在 body 中存在的形式，即使是在 .md 文件中，也依然使用这种形式存在
RE_IMAGE_OUTERHTML = r'<img .*?src="(index_files/[^"]+)"[^>]*>'


class WizInternalLink(object):
    """ 嵌入 html 正文中的为知笔记内部链接，可能是笔记，也可能是附件
    """
    # 原始链接的整个 HTML 内容，包括 <a href="link....">名称</a>
    outerhtml: str = None

    # 链接的 title
    title: str = None

    # 原始链接中的资源 guid，可能是 attachemnt 或者是 document
    guid: str = None

    # 值为 open_attachment 或者 open_document
    link_type: str = 'open_attachment'

    def __init__(self, outerhtml: str, guid: str, title: str, link_type: str) -> None:
        self.outerhtml = outerhtml
        self.guid = guid
        self.title = title
        self.link_type = link_type

    def __repr__(self) -> str:
        return f'<WizInternalLink {self.link_type}, {self.title}, {self.guid}>'


class WizImage(object):
    """ 在为知笔记文章中包含的本地图像

    在为知笔记中，本地图像不属于资源，也没有自己的 guid
    """
    # 原始图像的整个 HTML 内容，包括 <img src="index_files/name.jpg">
    outerhtml: str = None

    # 仅包含图像的 src 部分
    src: str = None

    # 图像文件的 Path 对象，在硬盘上的路径
    file: Path = None

    def __init__(self, outerhtml: str, src: str, note_extract_dir: Path) -> None:
        self.outerhtml = outerhtml
        self.src = src
        self.file = note_extract_dir.joinpath(src)

        if not self.file.exists():
            raise FileNotFoundError(f'找不到文件 {self.file}！')

    def __repr__(self) -> str:
        return f'<WizImage {self.src}, {self.outerhtml}>'


def parse_wiz_html(note_extract_dir: Path, title: str) -> tuple[str, list[WizInternalLink], list[WizImage]]:
    """ 在为知笔记文档的 index.html 中搜索内链的附件和文档链接
    """
    index_html = note_extract_dir.joinpath('index.html')
    if not index_html.is_file:
        raise FileNotFoundError(f'主文档文件不存在！ {index_html} |{title}|')
    html_body_bytes = index_html.read_bytes()
    # 早期版本的 html 文件使用的是 UTF-16 LE(BOM) 编码保存。最新的文件是使用 UTF-8(BOM) 编码保存。要判断编码进行解析
    enc = chardet.detect(html_body_bytes)
    html_body = html_body_bytes.decode(encoding=enc['encoding'])

    # 去掉换行符，早期版本的 html 文件使用了 \r\n 换行符，而且会切断 html 标记。替换掉换行符方便正则
    html_body = html_body.replace('\r\n', '')
    html_body = html_body.replace('\n', '')

    internal_links: list[WizInternalLink] = []

    open_attachments = re.finditer(RE_OPEN_ATTACHMENT_OUTERHTML, html_body, re.IGNORECASE)
    for open_attachement in open_attachments:
        link = WizInternalLink(
            open_attachement.group(0),
            open_attachement.group(2),
            open_attachement.group(3),
            open_attachement.group(1))
        internal_links.append(link)

    open_documents = re.finditer(RE_OPEN_DOCUMENT_OUTERHTML, html_body, re.IGNORECASE)
    for open_document in open_documents:
        link = WizInternalLink(
            open_document.group(0),
            open_document.group(2),
            open_document.group(4),
            open_document.group(1))
        internal_links.append(link)

    images: list[WizImage] = []
    image_match = re.finditer(RE_IMAGE_OUTERHTML, html_body, re.IGNORECASE)
    for image in image_match:
        img = WizImage(image.group(0), image.group(1), note_extract_dir)
        images.append(img)
    return html_body, internal_links, images


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


class JoplinInternalLink(object):
    """ 与 Wiz 内链不同，Joplin 内链包括 附件(链接到 resource)、图像(链接到 resource)、文档（链接到 note)
    """
    note_id: str
    resource_id: str

    # image / open_attachment / open_document
    link_type: str

    # 链接的 title
    title: str = None

    # 链接的整个文本内容，可能是 markdown 格式也可能是html格式，取决于 note_id 是何种格式
    outertext: str

    def __init__(self, note_id: str, resource_id: str, title: str, link_type: int, outertext:str='') -> None:
        self.note_id = note_id
        self.resource_id = resource_id
        self.title = title
        self.link_type = link_type
        self.outertext = outertext

    @property
    def id(self) -> str:
        return f'{self.note_id}-{self.resource_id}'


def gen_ilstr(is_markdown: bool, jil: JoplinInternalLink) -> str:
    """ 返回被替换的内链
    ilstr = internal link str
    """
    if is_markdown:
        body = f'[{jil.title}](:/{jil.resource_id})'
        if jil.link_type == 'image':
            return '!' + body
        return body
    if jil.link_type == 'image':
        return f'<img src=":/{jil.resource_id}" alt="{jil.title}">'
    return f'<a href=":/{jil.resource_id}">{jil.title}</a>'


def gen_end_ilstr(is_markdown: bool, jils: list[JoplinInternalLink]):
    """ 返回 body 底部要加入的内容
    ilstr = internal link str
    """
    if is_markdown:
        return '\n\n# 附件链接\n\n' + '\n'.join([ '- ' + gen_ilstr(is_markdown, jil) for jil in jils])
    body = ''.join([ f'<li>{gen_ilstr(is_markdown, jil)}</li>' for jil in jils])
    return f'<br><br><h1>附件链接</h1><ul>{body}</ul>'
    

def convert_joplin_body(body: str, is_markdown: bool, internal_links: list[JoplinInternalLink]) -> str:
    """ 将为知笔记中的 body 转换成 Joplin 内链
    """
    insert_to_end: list[JoplinInternalLink] = []
    for jil in internal_links:
        # 替换链接
        if jil.outertext:
            body = body.replace(jil.outertext, gen_ilstr(is_markdown, jil))
        # 所有的附件，需要在body 底部加入链接
        if jil.link_type == 'open_attachment':
            insert_to_end.append(jil)
    # 处理 markdown 转换
    if is_markdown:
        body = get_text(body)
    if insert_to_end:
        body += gen_end_ilstr(is_markdown, insert_to_end)
    return body