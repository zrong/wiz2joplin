##############################
# w2j.parser
# 解析为知笔记的 html 源文件
##############################

from pathlib import Path

def extract_wiz_inline_link():
    """ 从html 源码中解析出 wiz 内链
    """
    # wiz:open_attachment?guid=8337764c-f89d-4267-bdf2-2e26ff156098
    # wiz://open_attachment?guid=52935f17-c1bb-45b7-b443-b7ba1b6f854e

def extract_wiz_inline_link_open_document():
    # wiz://open_document?guid=c6204f26-f966-4626-ad41-1b5fbdb6829e&amp;kbguid=&amp;private_kbguid=69899a48-dc52-11e0-892c-00237def97cc
    pass

def parse_wiz_html(index_html: Path):
    html_body = index_html.read_text()