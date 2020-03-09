# coding: utf-8
from lxml.etree import Element
from zeit.importer import k4import
from zeit.importer.article import Article
from zeit.importer.article import sanitizeDoc
import lxml.etree
import mock
import os
import pkg_resources
import zeit.importer.testing
import zope.component


class K4ImportTest(zeit.importer.testing.TestCase):

    def test_configuration(self):
        config = {'importer': {
            'connector_url': 'foo',
            'k4_export_dir': '/foo',
            'k4_archive_dir': '/baa',
            'k4_highres_dir': 'batz',
            'import_root': 'http://xml.zeit.de/archiv-wf/archiv/',
            'import_root_in': 'http://xml.zeit.de/archiv-wf/archiv-in/',
            'import_config': 'http://xml.zeit.de/forms/importexport.xml',
            'ressortmap': 'http://xml.zeit.de/forms/printimport.xml',
            'access_source': 'http://xml.zeit.de/work/data/access.xml'
        }}

        k4import._configure(config)
        processed_config = zope.component.getUtility(
            zeit.importer.interfaces.ISettings)
        self.assertIn('connector_url', list(processed_config.keys()))

    def test_filename_normalization(self):
        norm_1 = k4import.mangleQPSName(
            'Streitgespr‰ch_Vitakasten'.decode('utf-8'))
        self.assertEqual(norm_1, 'Streitgespraech-Vitakasten')
        norm_2 = k4import.mangleQPSName('Kˆpfe der Zeit'.decode('utf-8'))
        self.assertEqual(norm_2, 'Koepfe-der-Zeit')
        norm_3 = k4import.mangleQPSName('÷-Scharinger'.decode('utf-8'))
        self.assertEqual(norm_3, 'Oe-Scharinger')
        norm_4 = k4import.mangleQPSName('HfjS_Portr‰t'.decode('utf-8'))
        self.assertEqual(norm_4, 'HfjS-Portraet')

    def test_sanatize_doc(self):
        xml = "<p>E</p>\r\n<p>in Test"
        self.assertEqual(sanitizeDoc(xml), '<p>Ein Test')

    def test_article_is_loaded(self):
        doc = self._get_doc()
        val = doc.doc.xpath("//attribute[@ns='http://namespaces.zeit.de/CMS/" +
                            "workflow' and @name='status']")[0].text
        self.assertEqual(val, 'import')
        self.assertEqual(
            doc.metadata[0],
            ('http://namespaces.zeit.de/CMS/workflow', 'status', 'import'))

    def test_single_value_from_metadata(self):
        doc = self._get_doc()
        jobname = doc.getAttributeValue(
            'http://namespaces.zeit.de/CMS/document', 'jobname')
        self.assertEqual(jobname, u'Sp\u2030te Flucht 89')

    def test_product_ids_dach(self):
        doc = self._get_doc()
        self.assertEqual(doc.get_product_id(None, 'A-Test'), 'ZEOE')
        self.assertEqual(doc.get_product_id(None, 'A_Test'), 'ZEOE')
        self.assertEqual(doc.get_product_id(None, 'CH-Teäst'), 'ZECH')
        self.assertEqual(doc.get_product_id(None, 'CH_Teäst'), 'ZECH')
        self.assertEqual(doc.get_product_id(None, 'ACH-Test'), 'ZEI')
        self.assertEqual(doc.get_product_id(None, 'ACH_Test'), 'ZEI')
        self.assertEqual(doc.get_product_id(None, 'S-Test'), 'ZESA')
        self.assertEqual(doc.get_product_id(None, 'S_Test'), 'ZESA')

    def test_publication_id(self):
        doc = self._get_doc()
        publication_id = doc.getAttributeValue(
            'http://namespaces.zeit.de/CMS/print', 'publication-id')
        product_id = self.settings['product_ids'].get(publication_id)
        self.assertEqual(product_id, 'ZEI')

    def test_pdf_it_should_be_set_correctly(self):
        doc = self._get_doc('MuM_Luxusautos.xml')
        pdf_id = doc.getAttributeValue(
            'http://namespaces.zeit.de/CMS/print', 'pdf_id')
        assert pdf_id == 'All'

    def test_creation_of_import_collections(self):
        k4import.ensure_collection(
            'http://xml.zeit.de/archiv-wf/archiv/ZEI/2009/40/feuilleton')
        res_type = self.connector[(
            'http://xml.zeit.de/archiv-wf/archiv/ZEI/2009/40/feuilleton')].type
        self.assertEqual(res_type, 'collection')

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
        product_id = self.settings['product_ids'].get(publication_id)
        jobname = doc.getAttributeValue(
            'http://namespaces.zeit.de/CMS/document', 'jobname')
        cname = k4import.mangleQPSName(jobname)
        doc.addAttributesToDoc(product_id, year, volume, cname)
        self.assertEqual(
            self._get_attr_val(doc, 'workflow', 'status'), 'import')
        self.assertEqual(
            self._get_attr_val(doc, 'workflow', 'ipad_template'), None)
        self.assertEqual(
            self._get_attr_val(doc, 'print', 'article_id'), '254475')
        self.assertEqual(
            self._get_attr_val(doc, 'workflow', 'importsource'), 'k4')
        self.assertEqual(
            self._get_attr_val(doc, 'print', 'erscheint'),
            '2009-09-24T07:00:00+00:00')
        self.assertEqual(
            self._get_attr_val(doc, 'document', 'date_first_released'),
            '2009-09-24T07:00:00+00:00')
        self.assertEqual(
            self._get_attr_val(doc, 'document', 'copyrights'),
            'DIE ZEIT, 24.09.2009 Nr. 40')
        self.assertEqual(
            self._get_attr_val(doc, 'document', 'page'), '55-55')
        self.assertEqual(
            self._get_attr_val(doc, 'document', 'ressort'), 'Kultur')
        self.assertEqual(
            self._get_attr_val(doc, 'print', 'ressort'), 'Feuilleton')
        self.assertEqual(
            self._get_attr_val(doc, 'workflow', 'id'),
            'ZEI-2009-40-Spaete-Flucht-89')
        self.assertEqual(
            self._get_attr_val(doc, 'workflow', 'running-volume'),
            'ZEI-2009-40')
        self.assertEqual(
            self._get_attr_val(doc, 'workflow', 'product-id'), 'ZEI')
        self.assertEqual(
            self._get_attr_val(doc, 'document', 'export_cds'), 'no')

    def test_change_pub_id_ressort_to_different_pup_id(self):
        doc = Article(pkg_resources.resource_filename(
            'zeit.importer', 'testdocs/AufmarschAtom.xml'))
        doc_id = doc.get_product_id(None, 'uninteresting-k4-filename')
        self.assertEqual(doc_id, 'ZESA')

    def test_normalize_whitespace(self):
        text = zeit.importer.article.normalize_and_strip_whitespace(object(), (
            ['this ', '  is a ', 'test\n  foo ba  foo ']))
        self.assertEqual(text[0], 'this')
        self.assertEqual(text[1], 'is a')
        self.assertEqual(text[2], 'test foo ba foo')
        doc = self._get_doc(filename='whitespace.xml')
        xpath = doc.doc.xpath('//p')
        self.assertEqual(xpath[0].text, u'Stra\xdfburg')
        self.assertEqual(xpath[1].text, 'Test some whitespace. Is OK!')
        self.assertEqual(xpath[2].text, 'This should be normalized')
        self.assertEqual(xpath[3].text, 'foo')

    def test_normalize_whitespace_with_mixed_content(self):
        doc = self._get_doc(filename='whitespace.xml')
        xpath = doc.doc.xpath('//p')
        self.assertEqual(xpath[4].text,
                         ('This is text, which should '
                          'not be trimmed incorrectly.'))
        self.assertEqual(xpath[5].text,
                         ('This is text, which should '
                          'not be trimmed incorrectly. But normalized.'))
        self.assertEqual(xpath[6].text,
                         ('This is text, with mixed content but we can '
                          'do trimming at the end.'))
        self.assertEqual(xpath[7].text,
                         ('This is text, with too much whitespace, '
                          'which should be normalized and trimmed.'))
        self.assertEqual(lxml.etree.tostring(xpath[8]), (
            '<p xmlns:f=\"http://namespaces.zeit.de/functions\">This is text, '
            '<strong> with too much whitespace, </strong> which cannot be '
            'trimmed.</p> '))

    def test_extract_and_move_elements(self):
        root = Element("article")
        head = Element("head")
        body = Element("body")
        root.append(head)
        root.append(body)

        for x in range(1, 5):
            body.append(Element("foo"))

        self.assertEqual(4, len(root.xpath("/article/body/foo")))

        root_2 = Element("root")
        zeit.importer.k4import.extract_and_move_xml_elements(
            root.xpath("//foo"), root_2)

        self.assertEqual(4, len(root_2.xpath("/root/foo")))
        self.assertEqual(0, len(root.xpath("/article/body/foo")))

    def test_process_boxes(self):
        articles = {
            "http://xml.zeit.de/Trump": (
                self._get_doc(filename='Trump.xml'), 'Trump')}
        boxes = {'http://xml.zeit.de/Trump-Kasten': (
            self._get_doc(filename='Trump-Kasten.xml'), 'Trump')}
        box_xml = boxes['http://xml.zeit.de/Trump-Kasten'][0].doc
        zeit.importer.k4import.process_boxes(boxes, articles)
        self.assertEqual(0, len(box_xml.xpath('//p')))
        article = articles['http://xml.zeit.de/Trump'][0].doc
        self.assertEqual(1, len(article.xpath('/article/body/box')))

    def test_process_not_corresponding_boxes(self):
        articles = {
            "http://xml.zeit.de/Obama": (
                self._get_doc(filename='Trump.xml'), 'Trump')}
        boxes = {'http://xml.zeit.de/Trump-Kasten': (
            self._get_doc(filename='Trump-Kasten.xml'), 'Trump')}
        boxes_return = zeit.importer.k4import.process_boxes(boxes, articles)
        self.assertEqual(
            'http://xml.zeit.de/Trump-Kasten', list(boxes_return.keys())[0])

    def test_process_boxes_should_ignore_errors(self):
        articles = {
            "http://xml.zeit.de/Trump": (
                self._get_doc(filename='Trump.xml'), 'Trump')}
        boxes = {'http://xml.zeit.de/Trump-Kasten': (
            self._get_doc(filename='Trump-Kasten.xml'), 'Trump')}
        extract = 'zeit.importer.k4import.extract_and_move_xml_elements'
        with mock.patch(extract) as extract:
            extract.side_effect = RuntimeError('provoked')
            # assertNothingRaised
            zeit.importer.k4import.process_boxes(boxes, articles)

    def test_put_content(self):
        articles = {
            "http://xml.zeit.de/Trump": (
                self._get_doc(filename='Trump.xml'), 'Trump')}
        zeit.importer.k4import.put_content(articles)
        connector = zope.component.getUtility(
            zeit.connector.interfaces.IConnector)
        res = connector['http://xml.zeit.de/Trump']
        doc = lxml.etree.parse(res.data)
        self.assertEqual(27, len(doc.xpath('/article/head/attribute')))
        self.assertEqual(31, len(res.properties))

    def test_access_override(self):
        doc = self._get_doc(filename='access.xml').doc
        val = doc.xpath("//attribute[@name='access']")[0].text
        self.assertEqual("registration", val)

        del self.settings['access_override_value']
        zeit.importer.k4import._configure_from_dav_xml()
        doc = self._get_doc(filename='access.xml').doc
        val = doc.xpath("//attribute[@name='access']")[0].text
        self.assertEqual("free", val)
        self.settings['access_override_value'] = 'registration'

    def test_access_mapping(self):
        del self.settings['access_override_value']
        zeit.importer.k4import._configure_from_dav_xml()
        access = zeit.importer.article.map_access
        self.assertEqual(
            ['registration'], access(object(), ['loginpflichtig']))
        self.assertEqual(
            ['abo'], access(object(), ['abopflichtig']))
        self.assertEqual(
            ['free'], access(object(), ['frei']))
        self.assertEqual(
            ['__skip_import__'], access(object(), ['something']))
        self.settings['access_override_value'] = 'registration'

    def test_create_image_reference(self):
        article = self._get_doc('Walser.xml')
        zon_images = article.doc.xpath('/article/head/zon-image')
        self.assertEqual(zon_images[0].get('vivi_name'), 'img-1')
        self.assertEqual(len(zon_images), 1)

    def test_get_prefixed_img_resource(self):
        xml = lxml.etree.parse(pkg_resources.resource_filename(
            'zeit.importer', 'testdocs/img_47210154_Walser.xml'))
        res = k4import.get_prefixed_img_resource(
            pkg_resources.resource_filename('zeit.importer', 'testdocs/'),
            xml, 'http://xml.zeit.de/base-id', 'prefix', 'img-1')
        self.assertEqual(
            'http://xml.zeit.de/base-id/prefix-img-1.jpg',
            res.id)

        file_path = pkg_resources.resource_filename(
            'zeit.importer',
            'testdocs/preview/47210/Familie '
            'Walser01b___30x40__AUGEN_47210154.jpg')
        self.assertEqual(len(res.data.read()), os.stat(file_path).st_size)

    def test_create_img_xml(self):
        article = self._get_doc('Walser.xml')
        input_dir = pkg_resources.resource_filename(
            'zeit.importer', 'testdocs/')
        elem = article.doc.xpath('/article/head/zon-image')[0]
        img_xml = lxml.etree.parse('%s%s' % (input_dir, elem.get('k4_id')))
        zon_img_xml = k4import.create_img_xml(img_xml, 'img-1')
        self.assertEqual(zon_img_xml.tag, 'image-group')
        attributes = zon_img_xml.findall('attribute')
        self.assertEqual(attributes[0].text, 'image-group')
        self.assertEqual(attributes[1].text, 'Bildunterzeile')
        self.assertEqual(attributes[2].text, 'img-1')
        self.assertEqual(attributes[3].text, 'Foto: Karin Rocholl')
        self.assertEqual(attributes[4].text, 'P14D')

    def test_get_xml_img_resource(self):
        article = self._get_doc('Walser.xml')
        input_dir = pkg_resources.resource_filename(
            'zeit.importer', 'testdocs/')
        elem = article.doc.xpath('/article/head/zon-image')[0]
        img_xml = lxml.etree.parse('%s%s' % (input_dir, elem.get('k4_id')))
        res = k4import.get_xml_img_resource(
            img_xml, 'http://xml.zeit.de/base-id', 'img-1')
        self.assertEqual(res.id, 'http://xml.zeit.de/base-id/img-1')
        self.assertEqual(
            '<image-group><attribute name="type" ns="',
            res.data.read()[0:40])

    def test_zon_image_should_reference_uniqueId(self):
        article = self._get_doc('Walser.xml')
        zeit.importer.k4import.set_zon_image_uniqueId(
            article,
            "http://xml.zeit.de/test")
        url = article.doc.xpath('/article/head/zon-image')[0].get("uniqueId")
        self.assertEqual(url, "http://xml.zeit.de/test/img-1")

    @mock.patch(
        'zeit.importer.k4import.copyExportToArchive', return_value=None)
    def test_import_should_process_images(self, copy_function):
        input_dir = pkg_resources.resource_filename(
            'zeit.importer', 'testdocs/')
        k4import.run_dir(input_dir, 'ZEI')
        col_id = (
            'http://xml.zeit.de/archiv-wf/archiv/'
            'ZEI/2017/13/zon-images/Walser')
        resources = list(self.connector.listCollection(col_id))
        self.assertEqual(u'img-1', resources[0][0])
        self.assertEqual(u'master-img-1.jpg', resources[1][0])
        self.assertEqual(u'preview-img-1.jpg', resources[2][0])

    def test_get_path_should_fail_with_specific_exception(self):
        with self.assertRaises(zeit.importer.k4import.FileNotFoundException):
            zeit.importer.k4import._get_path(u'i_do_not_exist')

        with self.assertRaises(zeit.importer.k4import.FileNotFoundException):
            zeit.importer.k4import._get_path(
                u'ZLeo Cover 03_2017 •_49811159.jpg')

        # We can currently not test, if `_get_path` behaves correctly with
        # all the encodings we discover in the K4 export result. This is due to
        # problems with how Apples HFS handles the encoding of a file name.
        # `_get_path` ist battle tested and proved to work in production,
        # though.
