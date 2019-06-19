import os
import wget
from lxml import etree
from urllib.request import urlopen
from html.parser import HTMLParser


class MyHTMLParser(HTMLParser):
    def __init__(self, predicate):
        super().__init__()
        self.journals = []
        self.state = False
        self.predicate = predicate

    def handle_starttag(self, tag, attrs):
        self.state = tag == 'a'

    def handle_data(self, data):
        text = data.strip()
        if self.state and len(text) > 0 and self.predicate(text):
            self.journals.append(data)


class PDFHTMLParser(HTMLParser):
    def __init__(self, predicate):
        super().__init__()
        self.journals = []
        self.predicate = predicate

    def handle_data(self, data):
        text = data.strip()
        if self.predicate(text):
            self.journals.append(data)


def parseXML(xml):
    handle, pdf_link, json_link = None, None, None

    if xml.decode().count('\n') <= 17:
        return handle, pdf_link, json_link
    root = etree.fromstring(xml)

    for appt in root.getchildren():
        handle = appt.attrib.get('handle')
        for elem in appt.getchildren():
            if elem.text:
                json_link = elem.attrib.get('rich')
                for t in elem:
                    pdf_link = t.attrib.get('data')
    return handle, pdf_link, json_link


url_root = "https://socionet.ru/~cyrcitec/newr-nbr/nberwo/"
xml_root = "http://no-xml.socionet.ru/~cyrcitec/newr-nbr/nberwo/"
html_root = urlopen(url_root).read().decode()
url_prefix = "http://no-xml.socionet.ru/~cyrcitec/"
url_prefix_len = len(url_prefix)

journals_catalogue = MyHTMLParser(lambda x: x.endswith('.xml'))
journals_catalogue.feed(html_root)


try:
    os.mkdir('experiment1')
except:
    pass

to_test = [
    '22986.xml', '20867.xml', '15174.xml', '21592.xml', '9413.xml', '7798.xml', '8918.xml',
    '7131.xml', '8269.xml', '19862.xml', '19035.xml', '14176.xml', '19979.xml']

for journal in to_test:
    try:
        journal_id, journal_link_pdf, journal_link_json = parseXML(urlopen(''.join([xml_root, journal])).read())
        if (journal_id is None) or (journal_link_pdf is None) or (journal_link_json is None):
            continue
    except:
        continue

    try:
        os.mkdir(f'experiment1/{journal_id}')
    except:
        pass
    try:
        _ = wget.download(journal_link_pdf, out=f'experiment1/{journal_id}/{journal_id}:orig.pdf')
    except:
        pass
    try:
        # http://no-xml.socionet.ru/~cyrcitec/jfmt.cgi?file=j-nbr/nberwo/0011.json
        _ = wget.download(f"{url_prefix}jfmt.cgi?file={journal_link_json[url_prefix_len:]}",
                          out=f'experiment1/{journal_id}/{journal_id}:orig.txt')
    except:
        pass
