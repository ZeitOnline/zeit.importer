from zeit.importer.interfaces import PRINT_NS, DOC_NS, WORKFLOW_NS
import lxml.etree
import logging
import os.path
import re
import zeit.importer.interfaces
import zope.component


log = logging.getLogger(__name__)
p_pattern = re.compile('<p>([a-z0-9])</p>\s*<p>', re.M | re.I)  # <p>V</p>


def sanitizeDoc(xml):
    """Cleans the doc from dirty k4markup."""
    xml = p_pattern.sub('<p>\\1', xml)
    return xml


def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level + 1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def normalize_and_strip_whitespace(context, text):
    return [re.sub("\s+", " ", t).strip() for t in text]


def normalize_whitespace(context, text):
    return [re.sub("\s+", " ", t) for t in text]


class Article(object):
    """Transforms k4xml to zeit article format."""

    def __init__(self, path):
        if not os.path.isfile(path):
            raise IOError('%s does not exists' % path)
        conf = zope.component.getUtility(zeit.importer.interfaces.ISettings)
        ns = lxml.etree.FunctionNamespace(
                'http://namespaces.zeit.de/functions')
        ns['normalize_whitespace'] = normalize_whitespace
        ns['normalize_and_strip_whitespace'] = normalize_and_strip_whitespace
        self.doc = conf['k4_stylesheet'](
            lxml.etree.parse(path), ressortmap_url="'%s'" % conf['ressortmap'])
        self.metadata = self.getAttributesFromDoc()
        self.product_id = None

    def getAttributesFromDoc(self):
        metas = self.doc.xpath('//head/attribute')

        props = []
        if metas:
            for m in metas:
                ns = m.get('ns')
                name = m.get('name')
                value = m.text if m.text is not None else ''
                props.append((ns, name, value))

        return props

    def getAttributeValue(self, ns, name):
        try:
            return [m[2] for m in self.metadata
                    if m[0] == ns and m[1] == name][0]
        except:
            return None

    def get_product_id(self, product_id_in, filename):
        """Detects product id of the document, by file-pattern matching or by
        doc-attribute."""
        conf = zope.component.getUtility(zeit.importer.interfaces.ISettings)
        if product_id_in is None:
            if filename.startswith('CH-') or filename.startswith('CH_'):
                self.product_id = 'ZECH'
            elif filename.startswith('A-') or filename.startswith('A_'):
                self.product_id = 'ZEOE'
            elif filename.startswith('S-') or filename.startswith('S_'):
                self.product_id = 'ZESA'
            else:
                # no product_id was given as command line argument
                # get publciation-id for print_ressort
                publication_id = self.getAttributeValue(
                    PRINT_NS, 'publication-id')
                if not publication_id:
                    raise "PublicationId not found '%s'" % (filename)

                ressort = self.getAttributeValue(PRINT_NS, 'ressort')
                if ressort:
                    publication_id = conf['publication_ids'].get(
                        (publication_id, ressort)) or publication_id
                self.product_id = conf['product_ids'].get(publication_id)
                if not self.product_id:
                    log.warning(
                        'PublicationId %s cannot be mapped.', publication_id)
        else:
            self.product_id = product_id_in
        return self.product_id

    def addAttributesToDoc(self, product_id, year, volume, cname):
        conf = zope.component.getUtility(zeit.importer.interfaces.ISettings)
        head = self.doc.xpath('//article/head')[0]
        attributes = [
            '<attribute ns="%s" name="id">%s-%s-%s-%s</attribute>' % (
                WORKFLOW_NS, product_id, year, volume, cname),
            '<attribute ns="%s" name="running-volume">%s-%s-%s</attribute>' % (
                WORKFLOW_NS, product_id, year, volume),
            '<attribute ns="%s" name="product-id">%s</attribute>' % (
                WORKFLOW_NS, product_id),
            '<attribute ns="%s" name="product-name">%s</attribute>' % (
                WORKFLOW_NS, conf['product_names'].get(product_id, '')),
            '<attribute ns="%s" name="export_cds">%s</attribute>' % (
                DOC_NS, 'no')
        ]
        for attr in attributes:
            head.append(lxml.etree.fromstring(attr))

    def addTitleToDoc(self, elems):
        if len(elems) > 0:
            body = self.doc.xpath('//article/body')
            elems.reverse()
            for e in elems:
                body[0].insert(0, e)

    def addBoxToDoc(self, elems):
        if len(elems) > 0:
            body = self.doc.xpath('//article/body')
            for e in elems:
                body[0].append(e)

    def to_string(self):
        indent(self.doc.getroot())
        xml = lxml.etree.tostring(
            self.doc, encoding="utf-8", xml_declaration=True)
        xml = sanitizeDoc(xml)  # <p>V</p> etc
        return xml
