"""Plain-text presentation of collected fields; never rewrites source data."""

import html
import re
from html.parser import HTMLParser


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif not self.hidden and tag in {"br", "p", "div", "li", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {"p", "div", "li", "section"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def display_text(value):
    if value is None:
        return None
    text = str(value)
    for _ in range(2):
        text = html.unescape(text)
    if re.search(r"</?[a-zA-Z][^>]*>", text):
        parser = _TextParser()
        parser.feed(text)
        text = "".join(parser.parts)
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line) or None
