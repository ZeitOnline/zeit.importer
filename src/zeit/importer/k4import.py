# coding: utf-8
from zeit.connector.resource import Resource
from zeit.importer.article import Article
from zeit.importer.interfaces import DOC_NS, PRINT_NS
import ConfigParser
import StringIO
import datetime
import logging
import logging.config
import lxml.etree
import optparse
import os
import pkg_resources
import re
import shutil
import urlparse
import zeit.connector.connector
import zeit.connector.interfaces
import zeit.importer.interfaces
import zope.component


log = logging.getLogger(__name__)


def mangleQPSName(qps_name):
    qps_name = qps_name.encode('utf-8')
    qps_name = qps_name.replace("ƒ", "Ae")  # Ä
    qps_name = qps_name.replace("‹", "Ue")  # Ü
    qps_name = qps_name.replace("÷", "Oe")  # Ö
    qps_name = qps_name.replace("‰", "ae")  # ä
    qps_name = qps_name.replace("¸", "ue")  # ü
    qps_name = qps_name.replace("ˆ", "oe")  # ö
    qps_name = qps_name.replace("ﬂ", "ss")
    qps_name = qps_name.replace("&", "")
    qps_name = qps_name.replace("?", "")
    qps_name = qps_name.strip('_- ')
    cname = re.compile('[\ \_.:;#+*/\']').sub('-', qps_name)
    cname = re.compile('[^A-Za-z0-9\-]').sub('', cname)
    cname = re.compile('-+').sub('-', cname)
    return cname


def ensure_collection(unique_id):
    """If the target collection does not exist, it will be created."""
    connector = zope.component.getUtility(zeit.connector.interfaces.IConnector)
    path = urlparse.urlparse(unique_id).path.split('/')[1:]
    unique_id = 'http://xml.zeit.de'
    for segment in path:
        unique_id = os.path.join(unique_id, segment)
        try:
            connector[unique_id]
        except KeyError:
            name = os.path.basename(unique_id)
            res = Resource(unique_id, name, 'collection',
                           StringIO.StringIO(''))
            connector.add(res)
            log.debug('Created collection %s', unique_id)
    return unique_id


def copyExportToArchive(input_dir):
    settings = zope.component.getUtility(zeit.importer.interfaces.ISettings)
    today = datetime.datetime.today()
    archive_path = os.path.normpath('%s/%s/%s' % (
        settings['k4_archive_dir'],
        today.strftime("%Y"),
        today.strftime("%m-%d-%a")))
    if os.path.isdir(archive_path):
        for i in range(1, 20):
            tmp_path = '%s-%d' % (archive_path, i)
            if os.path.isdir(tmp_path):
                continue
            else:
                archive_path = tmp_path
                break

    shutil.copytree(input_dir, archive_path)
    log.info('Copied input articles from %s to %s', input_dir, archive_path)

    if input_dir == settings['k4_export_dir']:
        log.info('Cleaning input directory %s', input_dir)
        for f in [os.path.normpath('%s/%s' % (settings['k4_export_dir'], f))
                  for f in os.listdir(settings['k4_export_dir'])]:
            if os.path.isfile(f):
                os.remove(f)


def run_dir(input_dir, product_id_in):
    if not os.path.isdir(input_dir):
        raise IOError("No such directory '%s'" % (input_dir,))

    connector = zope.component.getUtility(zeit.connector.interfaces.IConnector)
    settings = zope.component.getUtility(zeit.importer.interfaces.ISettings)

    count = 0
    cnames = []

    k4_files = os.listdir(input_dir)
    boxes = {}
    articles = {}
    images = []
    for (k4_filename, k4_filepath) in [
            (f, os.path.join(input_dir, f)) for f in k4_files]:
        try:
            if (os.path.isdir(k4_filepath)):
                continue
            elif k4_filename[0:4] == 'img_':
                # We handle img-xml, when it is discovered inside the article
                # XML.
                continue

            log.info('Importing %s', k4_filename)
            doc = Article(k4_filepath)

            jobname = doc.getAttributeValue(DOC_NS, 'jobname')
            if not jobname:
                raise Exception("Original name not found '%s'" % k4_filepath)
            log.debug('k4name %s', jobname)

            cname = jobname
            if cname.endswith('.xml'):
                cname = cname[:-4]
            cname = mangleQPSName(cname)
            if cname[0] == '_':
                cname = cname[1:]
            # Deduplicate filenames
            if cname in cnames:
                cname = cname + str(count)
            cnames.append(cname)

            # set extra metadata
            doc.metadata.append(
                ('http://namespaces.zeit.de/CMS/document', 'file-name', cname))
            doc.metadata.append(
                ('http://namespaces.zeit.de/CMS/document', 'export_cds', 'no'))

            # create the new resource
            log.debug('urlified %s', cname)

            # get infos for archive paths
            year = doc.getAttributeValue(DOC_NS, 'year')
            volume = doc.getAttributeValue(DOC_NS, 'volume')
            print_ressort = doc.getAttributeValue(PRINT_NS, 'ressort')

            product_id = doc.get_product_id(product_id_in, k4_filename)
            log.debug('product_id %s ', product_id)

            import_folders = []
            if not all([year, volume, print_ressort]):
                raise ValueError('Missing metadata in %s', cname)

            print_ressort = mangleQPSName(print_ressort).lower()

            import_root = ensure_collection(
                os.path.join(settings['import_root'], product_id, year,
                             volume, print_ressort))
            import_folders.append(import_root)

            import_root_in = ensure_collection(
                os.path.join(settings['import_root_in'], product_id, year,
                             volume, print_ressort))
            import_folders.append(import_root_in)

            img_base_id = ensure_collection(
                    os.path.join(settings['import_root'], product_id,
                                 year, volume, 'zon-images', cname))

            images = images + create_image_resources(
                input_dir, doc, img_base_id)

            doc.addAttributesToDoc(product_id, year, volume, cname)
            new_xml = doc.to_string()
            for import_folder in import_folders:
                unique_id = os.path.join(import_folder, cname)
                try:
                    connector[unique_id]
                    log.info("%s wurde _nicht_ neu importiert", unique_id)
                    continue
                except KeyError:
                    if new_xml and 'Kasten' in unique_id:
                        boxes[unique_id] = (doc, cname)
                    elif new_xml:
                        articles[unique_id] = (doc, cname)

            count = count + 1
            log.info('Done importing %s', cname)

        except Exception:
            log.error('Error', exc_info=True)
            continue

    unintegrated_boxes = process_boxes(boxes, articles)
    content = {}
    content.update(articles)
    content.update(unintegrated_boxes)
    put_content(content)
    put_images(images)

    if count > 0:
        copyExportToArchive(input_dir)
    else:
        log.warning('No documents to import found in %s', input_dir)


def put_content(resources):
    connector = zope.component.getUtility(zeit.connector.interfaces.IConnector)
    for unique_id in resources.keys():
        doc, cname = resources[unique_id]
        res = Resource(
            unique_id, cname, 'article', StringIO.StringIO(doc.to_string()),
            contentType='text/xml')
        for prop in doc.metadata:
            prop_val = re.sub(r'\&', ' + ', prop[2])
            res.properties[(prop[1], prop[0])] = (prop_val)
        log.info('Storing in CMS as %s/%s', unique_id, cname)
        connector.add(res)


def put_images(images):
    connector = zope.component.getUtility(zeit.connector.interfaces.IConnector)
    for image in images:
        connector.add(image)


def process_boxes(boxes, articles):
    no_corresponding_article = {}
    for box_id in boxes.keys():
        # Find belonging article
        box_doc, box_cname = boxes[box_id]
        box_xml = box_doc.doc
        article_id = re.sub('-Kasten.*$', '', box_id)

        if articles.get(article_id) is None:
            no_corresponding_article[box_id] = boxes[box_id]
            continue

        doc, cname = articles.get(article_id)
        article = doc.doc

        log.info('Process box %s for %s', box_id, article_id)
        # Extract coordinates and add to article
        extract_and_move_xml_elements(
            box_xml.find("//Frame"), article.find('//Frames')[0])

        new_box = lxml.etree.Element("box")
        article.find('//body').append(new_box)
        extract_and_move_xml_elements(
             box_xml.find("//body").getchildren(), new_box)
    return no_corresponding_article


def extract_and_move_xml_elements(elements, new_parent):
    for element in elements:
        element.getparent().remove(element)
        new_parent.append(element)


def load_access_mapping(access_source):
    return {e.get('k4_id'): e.get('id') for e in access_source.xpath("//type")}


class ConnectorResolver(lxml.etree.Resolver):

    def resolve(self, url, id, context):
        if not url.startswith('http://xml.zeit.de/'):
            return None
        connector = zope.component.getUtility(
            zeit.connector.interfaces.IConnector)
        return self.resolve_file(connector[url].data, context)


def load_configuration():
    connector = zope.component.getUtility(zeit.connector.interfaces.IConnector)
    settings = zope.component.getUtility(zeit.importer.interfaces.ISettings)

    try:
        resource = connector[settings['import_config']]
    except KeyError:
        raise ValueError('Import configuration file %s not found',
                         settings.get('import_config', ''))

    settings['product_names'] = {}
    settings['product_ids'] = {}
    settings['publication_ids'] = {}
    tree = lxml.etree.fromstring(resource.data.read())
    for p in tree.xpath('/config/product'):
        k4_id = p.findtext('k4id')
        label = p.findtext('label')
        id = p.get('id')
        if k4_id:
            settings['product_names'][id] = label
            settings['product_ids'][k4_id] = id
            for ressort in p.xpath('ressort'):
                settings['publication_ids'][
                    (k4_id, ressort.get('name'))] = ressort.get('id')

    try:
        connector[settings['ressortmap']]
    except KeyError:
        raise ValueError('Ressortmap file %s not found',
                         settings.get('ressortmap', ''))

    parser = lxml.etree.XMLParser()
    parser.resolvers.add(ConnectorResolver())
    settings['k4_stylesheet'] = lxml.etree.XSLT(lxml.etree.parse(
        pkg_resources.resource_filename(
            __name__, 'stylesheets/k4import.xslt'), parser=parser))
    settings['normalize_whitespace'] = lxml.etree.XSLT(lxml.etree.parse(
        pkg_resources.resource_filename(
            __name__, 'stylesheets/normalize_whitespace.xslt'), parser=parser))

    access_source = lxml.etree.parse(connector[settings['access_source']].data)
    settings['access_mapping'] = load_access_mapping(access_source)


def create_image_resources(input_dir, doc, img_base_id):
    img_resources = []
    for elem in doc.doc.xpath("/article/head/zon-image"):
        vivi_name = elem.get('vivi_name')
        img_xml = lxml.etree.parse(os.path.join(input_dir, elem.get('k4_id')))
        img_resources.append(get_xml_img_resource(
            img_xml, img_base_id, vivi_name))
        img_resources.append(get_preview_img_resource(
            input_dir, img_xml, img_base_id, vivi_name))
    return img_resources


def get_xml_img_resource(img_xml, img_base_id, name):
    xml = create_img_xml(img_xml)
    return Resource(
        os.path.join(img_base_id, name), name, 'image-xml',
        StringIO.StringIO(lxml.etree.tostring(xml)), contentType='text/xml')


def get_preview_img_resource(input_dir, img_xml, img_base_id, name):
    normpath = '/'.join(
        img_xml.find('/HEADER/LowResPath').text.replace(
            '\\', '/').split('/')[1:])
    path = os.path.join(input_dir, normpath)
    name = 'preview-%s.jpg' % (name)
    return Resource(
        os.path.join(img_base_id, name), name, 'image', file(path),
        contentType='image/jpeg')


def create_img_xml(xml):
    img_group = lxml.etree.Element('image-group')

    meta_type = lxml.etree.Element('attribute',
                                   ns='http://namespaces.zeit.de/CMS/meta',
                                   name='type')
    meta_type.text = 'image-group'
    img_group.append(meta_type)
    img_alt = lxml.etree.Element('attribute',
                                 ns='http://namespaces.zeit.de/CMS/image',
                                 name='alt')
    img_alt.text = xml.find('/HEADER/DESCRIPTION').get('value')
    img_group.append(img_alt)
    img_caption = lxml.etree.Element('attribute',
                                     ns='http://namespaces.zeit.de/CMS/image',
                                     name='caption')
    img_caption.text = xml.find('/HEADER/BUZ').get('value')
    img_group.append(img_caption)
    img_master = lxml.etree.Element('attribute',
                                    ns='http://namespaces.zeit.de/CMS/image',
                                    name='master_images')
    img_master.text = 'master-%s' % (
            xml.find('/HEADER/LowResPath').text.split('\\')[-1])
    img_group.append(img_master)
    img_copyrights = lxml.etree.Element(
            'attribute',
            ns='http://namespaces.zeit.de/CMS/document',
            name='copyrights')
    img_copyrights.text = xml.find('/HEADER/CREDITS').text
    img_group.append(img_copyrights)
    return img_group


def main():
    parser = optparse.OptionParser("usage: %prog [options] arg")
    parser.add_option("-i", "--indir", dest="input_dir",
                      help="directory with the k4 export files")
    parser.add_option("-p", "--productid", dest="product_id",
                      help="product id to be used with every article")
    parser.add_option("-c", "--config", dest="config_file",
                      help="path to configuration file")
    (options, args) = parser.parse_args()

    if not options.config_file:
        options.config_file = os.environ.get('ZEIT_IMPORTER_CONFIG')
    if not options.config_file:
        raise ValueError('A configuration file is required.')

    config = ConfigParser.ConfigParser()
    config.read([options.config_file])

    # Inspired by pyramid.paster.setup_logging().
    if config.has_section('loggers'):
        path = os.path.abspath(options.config_file)
        logging.config.fileConfig(path, dict(
            __file__=path, here=os.path.dirname(path)))

    settings = dict(config.items('importer'))
    zope.component.provideUtility(settings, zeit.importer.interfaces.ISettings)
    zope.component.provideUtility(zeit.connector.connector.Connector(
        {'default': settings['connector_url']}))
    load_configuration()

    if not options.input_dir:
        options.input_dir = settings['k4_export_dir']
        log.info('No input directory given, assuming %s', options.input_dir)

    try:
        log.info('Start import of %s to %s', options.input_dir,
                 settings['import_root'])
        run_dir(options.input_dir, options.product_id)
    except Exception:
        log.error('Error', exc_info=True)
        raise
