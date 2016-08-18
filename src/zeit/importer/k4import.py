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


def prepareColl(product_id, year, volume, print_ressort):
    """If the target collection does not exist, it will be created."""
    connector = zope.component.getUtility(zeit.connector.interfaces.IConnector)
    settings = zope.component.getUtility(zeit.importer.interfaces.ISettings)
    for d in [settings['import_root'], settings['import_root_in']]:
        coll_path = d
        parts = [product_id, year, volume, print_ressort]
        for p in parts:
            coll_path = os.path.join(coll_path, p)
            coll_create = None
            try:
                connector[coll_path]
            except KeyError:
                coll_create = True

            if coll_create:
                coll_name = os.path.basename(coll_path)
                col = Resource(coll_path, coll_name, 'collection',
                               StringIO.StringIO(''))
                connector.add(col)
                log.debug('Created collection %s', coll_path)


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
    for (k4_filename, k4_filepath) in [
            (f, os.path.join(input_dir, f)) for f in k4_files]:
        try:
            if (os.path.isdir(k4_filepath)):
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

            cms_paths = []
            if not all([year, volume, print_ressort]):
                raise ValueError('Missing metadata in %s', cname)
            print_ressort = mangleQPSName(print_ressort).lower()
            cms_paths.append(settings['import_root'] + '%s/%s/%s/%s/%s' % (
                product_id, year, volume, print_ressort, cname))
            cms_paths.append(
                settings['import_root_in'] + '%s/%s/%s/%s/%s' % (
                    product_id, year, volume, print_ressort, cname))
            log.debug(
                '%s, %s, %s, %s', product_id, year, volume, print_ressort)
            prepareColl(product_id, year, volume, print_ressort)

            doc.addAttributesToDoc(product_id, year, volume, cname)
            new_xml = doc.to_string()

            for cms_id in cms_paths:
                log.info('Storing in CMS as %s/%s', cms_id, cname)
                check_resource = None
                try:
                    check_resource = connector[cms_id]
                except KeyError, e:
                    log.info(e)

                if check_resource:
                    log.info(cms_id + "... wurde _nicht_ neu importiert")
                    continue

                if new_xml:
                    res = Resource(
                        cms_id, cname, 'article', StringIO.StringIO(new_xml),
                        contentType='text/xml')
                    for prop in doc.metadata:
                        prop_val = re.sub(r'\&', ' + ', prop[2])
                        res.properties[(prop[1], prop[0])] = (prop_val)
                    connector.add(res)
            count = count + 1
            log.info('Done importing %s', cname)

        except Exception:
            log.error('Error', exc_info=True)
            continue

    if count > 0:
        copyExportToArchive(input_dir)
    else:
        log.warning('No documents to import found in %s', input_dir)


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
    tree = lxml.etree.fromstring(resource.data.read())
    for p in tree.xpath('/config/product'):
        k4_id = p.findtext('k4id')
        label = p.findtext('label')
        id = p.get('id')
        if k4_id:
            settings['product_names'][id] = label
            settings['product_ids'][k4_id] = id

    settings['k4_stylesheet'] = lxml.etree.XSLT(lxml.etree.parse(
        pkg_resources.resource_filename(
            __name__, 'stylesheets/k4import.xslt')))


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
