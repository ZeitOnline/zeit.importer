#!/usr/bin/python
# -*- coding: utf-8 -*-

from zeit.importer.article import Article
from zeit.importer.article import sanitizeDoc
from zeit.importer import k4import
import os.path
import pkg_resources
import unittest
import zeit.cms.testing
import zeit.connector.mock
import zeit.connector.resource
import zeit.importer.interfaces
import zope.component


settings = {
    'connector_url': 'mocked',
    'k4_export_dir': '/var/cms/import/k4incoming/',
    'k4_archive_dir': '/var/cms/import/old/',
    'import_root': 'http://xml.zeit.de/archiv-wf/archiv/',
    'import_root_in': 'http://xml.zeit.de/archiv-wf/archiv-in/',
    'import_config': 'http://xml.zeit.de/forms/importexport.xml',
    'ressortmap': 'http://xml.zeit.de/forms/printimport-ressortmap.xml',
}


def getConnector():
    connector = zeit.connector.mock.Connector('http://xml.zeit.de/')
    for name in ['importexport.xml', 'printimport-ressortmap.xml']:
        connector.add(zeit.connector.resource.Resource(
            'http://xml.zeit.de/forms/%s' % name, name,
            'text', pkg_resources.resource_stream(
                __name__, '/testdocs/ipool/%s' % name),
            contentType='text/xml'))
    return connector


class K4ImportTest(unittest.TestCase):

    def _get_doc(self):
        return Article(
            os.path.dirname(__file__)+'/testdocs/Sp_te_Flucht_89.xml')

    def setUp(self):
        self.connector = getConnector()
        zope.component.provideUtility(self.connector)
        zope.component.provideUtility(
                settings, zeit.importer.interfaces.ISettings)
        k4import.load_configuration()
        self.settings = zope.component.getUtility(
                zeit.importer.interfaces.ISettings)

    def test_product_values(self):
        self.assertEquals(
                self.settings['product_ids']['1153836019'], 'ZTCS')
        self.assertEquals(
                self.settings['product_names']['ZMLB'], 'ZEIT Magazin')

    def test_filename_normalization(self):
        norm_1 = k4import.mangleQPSName(
                'Streitgespr‰ch_Vitakasten'.decode('utf-8'))
        self.assertEquals(norm_1, 'Streitgespraech-Vitakasten')
        norm_2 = k4import.mangleQPSName('Kˆpfe der Zeit'.decode('utf-8'))
        self.assertEquals(norm_2, 'Koepfe-der-Zeit')
        norm_3 = k4import.mangleQPSName('÷-Scharinger'.decode('utf-8'))
        self.assertEquals(norm_3, 'Oe-Scharinger')
        norm_4 = k4import.mangleQPSName('HfjS_Portr‰t'.decode('utf-8'))
        self.assertEquals(norm_4, 'HfjS-Portraet')

    def test_sanatize_doc(self):
        xml = "<p>E</p>\r\n<p>in Test"
        self.assertEquals(sanitizeDoc(xml), '<p>Ein Test')

    def test_article_is_loaded(self):
        doc = self._get_doc()
        val = doc.doc.xpath("//attribute[@ns='http://namespaces.zeit.de/CMS/" +
                            "workflow' and @name='status']")[0].text
        self.assertEquals(val, 'import')
        self.assertEquals(doc.metadata[0],
                          ('http://namespaces.zeit.de/CMS/workflow',
                              'status', 'import'))

    def test_single_value_from_metadata(self):
        doc = self._get_doc()
        jobname = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/document', 'jobname')
        self.assertEquals(jobname, u'Sp\u2030te Flucht 89')

    def test_product_ids_dach(self):
        doc = self._get_doc()
        self.assertEquals(doc.get_product_id(None, 'A-Test'), 'ZEOE')
        self.assertEquals(doc.get_product_id(None, 'A_Test'), 'ZEOE')
        self.assertEquals(doc.get_product_id(None, 'CH-Teäst'), 'ZECH')
        self.assertEquals(doc.get_product_id(None, 'CH_Teäst'), 'ZECH')
        self.assertEquals(doc.get_product_id(None, 'ACH-Test'), 'ZEI')
        self.assertEquals(doc.get_product_id(None, 'ACH_Test'), 'ZEI')
        self.assertEquals(doc.get_product_id(None, 'S-Test'), 'ZESA')
        self.assertEquals(doc.get_product_id(None, 'S_Test'), 'ZESA')

    def test_publication_id(self):
        doc = self._get_doc()
        publication_id = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/print', 'publication-id')
        product_id = settings['product_ids'].get(publication_id)
        self.assertEquals(product_id, 'ZEI')

    def test_creation_of_import_collections(self):
        doc = self._get_doc()
        year = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/document', 'year')
        volume = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/document', 'volume')
        print_ressort = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/print', 'ressort')
        print_ressort = k4import.mangleQPSName(print_ressort).lower()
        publication_id = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/print', 'publication-id')
        product_id = settings['product_ids'].get(publication_id)
        k4import.prepareColl(product_id, year, volume, print_ressort)
        res_type = self.connector[(
            'http://xml.zeit.de/archiv-wf/archiv/ZEI/2009/40/feuilleton')].type
        self.assertEquals(res_type, 'collection')
        res_type = self.connector[(
            'http://xml.zeit.de/archiv-wf/archiv-in'
            '/ZEI/2009/40/feuilleton')].type
        self.assertEquals(res_type, 'collection')

    def _get_attr_val(self, doc, ns, name):
        xpath = ('//head/attribute[@ns="http://namespaces.zeit.de/CMS/{}" '
                 'and @name="{}"]').format(ns, name)
        return doc.doc.xpath(xpath)[0].text

    def test_add_attributes_to_doc(self):
        doc = self._get_doc()
        year = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/document', 'year')
        volume = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/document', 'volume')
        print_ressort = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/print', 'ressort')
        print_ressort = k4import.mangleQPSName(print_ressort).lower()
        publication_id = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/print', 'publication-id')
        product_id = settings['product_ids'].get(publication_id)
        jobname = doc.getAttributeValue(
                'http://namespaces.zeit.de/CMS/document', 'jobname')
        cname = k4import.mangleQPSName(jobname)
        doc.addAttributesToDoc(product_id, year, volume, cname)
        self.assertEquals(
                self._get_attr_val(doc, 'workflow', 'status'), 'import')
        self.assertEquals(
                self._get_attr_val(doc, 'workflow', 'ipad_template'), None)
        self.assertEquals(
                self._get_attr_val(doc, 'print', 'article_id'), '254475')
        self.assertEquals(
                self._get_attr_val(doc, 'workflow', 'importsource'), 'k4')
        self.assertEquals(
                self._get_attr_val(doc, 'document', 'erscheint'), '24.09.2009')
        self.assertEquals(
                self._get_attr_val(doc, 'document', 'date_first_released'),
                '2009-09-24T06:00:00+00:00')
        self.assertEquals(
                self._get_attr_val(doc, 'document', 'copyrights'),
                'DIE ZEIT, 24.09.2009 Nr. 40')
        self.assertEquals(
                self._get_attr_val(doc, 'document', 'page'), '55-55')
        self.assertEquals(
                self._get_attr_val(doc, 'document', 'ressort'), 'Kultur')
        self.assertEquals(
                self._get_attr_val(doc, 'print', 'ressort'), 'Feuilleton')
        self.assertEquals(
                self._get_attr_val(doc, 'workflow', 'id'),
                'ZEI-2009-40-Spaete-Flucht-89')
        self.assertEquals(
                self._get_attr_val(doc, 'workflow', 'running-volume'),
                'ZEI-2009-40')
        self.assertEquals(
                self._get_attr_val(doc, 'workflow', 'product-id'), 'ZEI')
        self.assertEquals(
                self._get_attr_val(doc, 'document', 'export_cds'), 'no')

    def test_change_pub_id_ressort_to_different_pup_id(self):
        doc = Article(os.path.dirname(__file__)+'/testdocs/AufmarschAtom.xml')
        doc_id = doc.get_product_id(None, 'uninteresting-k4-filename')
        self.assertEquals(doc_id, 'ZESA')
