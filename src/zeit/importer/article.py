from zeit.importer import PRINT_NS, DOC_NS, WORKFLOW_NS
import lxml.etree
import os.path
import re

K4_STYLESHEET = os.path.dirname(__file__) + '/stylesheets/k4import.xslt'
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


def transform_k4(k4xml_path):
    """Transforms k4xml to zeit article format."""
    if not os.path.isfile(k4xml_path):
        raise IOError('%s does not exists' % k4xml_path)

    xslt_doc = lxml.etree.parse(K4_STYLESHEET)
    transform = lxml.etree.XSLT(xslt_doc)

    doc = lxml.etree.parse(k4xml_path)
    result = transform(doc)

    return result


class TransformedArticle(object):

    def __init__(self, doc, ipool, logger=False):
        self.doc = doc
        self.ipool = ipool
        self.logger = logger
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

    def get_publication_id_by_ressort(self, publication_id, ressort):
        if not ressort:
            return publication_id

        if self.ipool.ressort_map.get((publication_id, ressort)):
            return self.ipool.ressort_map.get((publication_id, ressort))

        return publication_id

    def get_product_id(self, product_id_in, filename):
        """Detects product id of the document, by file-pattern matching or by
        doc-attribute."""
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
                publication_id = self.get_publication_id_by_ressort(
                    publication_id, ressort)

                # detect the Produktid
                self.product_id = self.ipool.product_map.get(publication_id)
                if not self.product_id:
                    self.logger.warning(
                        'PublicationId %s cannot be mapped.', publication_id)
        else:
            self.product_id = product_id_in
        return self.product_id

    def addAttributesToDoc(self, product_id, year, volume, cname):
        head = self.doc.xpath('//article/head')[0]
        attributes = [
            '<attribute ns="%s" name="id">%s-%s-%s-%s</attribute>' % (
                WORKFLOW_NS, product_id, year, volume, cname),
            '<attribute ns="%s" name="running-volume">%s-%s-%s</attribute>' % (
                WORKFLOW_NS, product_id, year, volume),
            '<attribute ns="%s" name="product-id">%s</attribute>' % (
                WORKFLOW_NS, product_id),
            '<attribute ns="%s" name="product-name">%s</attribute>' % (
                WORKFLOW_NS, self.ipool.products.get(product_id, '')),
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
