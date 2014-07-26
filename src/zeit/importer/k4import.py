# -*- coding: utf-8 -*-
from optparse import OptionParser
from zeit.connector.resource import Resource
from zeit.importer import DOC_NS, PRINT_NS
from zeit.importer import add_file_logging
from zeit.importer.article import TransformedArticle, transform_k4
from zeit.importer.ipoolconfig import IPoolConfig
import StringIO
import datetime
import logging
import os
import re
import shutil
import sys

logger = logging.getLogger(__name__)

# XXX: Could be refactores to something smarter than globals
CONNECTOR_URL = 'http://zip6.zeit.de:9000/cms/'
CMS_ROOT='http://xml.zeit.de/'
IMPORT_ROOT = 'http://xml.zeit.de/archiv-wf/archiv/'
IMPORT_ROOT_IN = 'http://xml.zeit.de/archiv-wf/archiv-in/'
K4_EXPORT_DIR = '/var/cms/import/k4incoming/'
K4_ARCHIVE_DIR = '/var/cms/import/old/'
IPOOL_CONF = 'http://xml.zeit.de/forms/importexport.xml'

extrafile_pattern = re.compile('^(kasten|titel)-', re.I)


def mangleQPSName(qps_name):
    # - [ ] ersetzt werden ä,ö,ü,ß in ae,oe,ue,ss
    # - [ ] ersetzt wird _ . : ; # + * / in -
    # - [ ] doppelte sonderzeichen entfernen
    # - [ ] der rest per regexp- alphabet
    # qps_name = qps_name.lower()
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
    # cname = mangleName(urllib.unquote_plus(cname))
    cname = re.compile('-+').sub('-', cname)
    return cname


def prepareColl(connector, product_id, year, volume, print_ressort):
    '''
        if target collection does not exist, it will be created
    '''
    for d in [IMPORT_ROOT, IMPORT_ROOT_IN]:
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
                logger.info("collection %s created" % coll_path)


def moveExportToArchive(input_dir):
    '''
        copies files to local archive
    '''
    today = datetime.datetime.today()
    archive_path = os.path.normpath('%s/%s/%s' % (
        K4_ARCHIVE_DIR, today.strftime("%Y"), today.strftime("%m-%d-%a")))
    if os.path.isdir(archive_path):
        for i in range(1, 20):
            tmp_path = '%s-%d' % (archive_path, i)
            if os.path.isdir(tmp_path):
                continue
            else:
                archive_path = tmp_path
                break

    shutil.copytree(input_dir, archive_path)
    logger.info("Input articles copied to  %s ..." % archive_path)

    if input_dir == K4_EXPORT_DIR:
        # when standard input dir, do some cleanup in that dir
        for f in [os.path.normpath('%s/%s' % (K4_EXPORT_DIR, f))
                  for f in os.listdir(K4_EXPORT_DIR)]:
            if os.path.isfile(f):
                os.remove(f)
        logger.info("Input dir %s cleaned...." % input_dir)


def run_dir(connector, input_dir, product_id_in):

    if not os.path.isdir(input_dir):
        raise IOError("No such directory '%s'" % (input_dir,))

    if not connector:
        raise EnvironmentError("No connector given")

    try:
        ipool = IPoolConfig(connector[IPOOL_CONF])
    except:
        raise EnvironmentError("Infopool config missing")

    count = 0
    cnames = []

    k4_files = os.listdir(input_dir)
    for (k4_filename, k4_filepath) in [
            (f, os.path.join(input_dir, f)) for f in k4_files]:
        try:
            # skip dirs
            if (os.path.isdir(k4_filepath)):
                continue

            # if extrafile_pattern.match(k4_filename):
            #   logger.info('**** EXCLUDE %s ****\n' % k4_filename)

            logger.info('**** STARTING %s ****' % k4_filename)
            new_doc = transform_k4(k4_filepath)

            # here we have a new document to work with
            doc = TransformedArticle(new_doc, ipool, logger)

            # get original name
            jobname = doc.getAttributeValue(DOC_NS, 'jobname')
            if not jobname:
                raise Exception("Original name not found '%s'" % k4_filepath)

            logger.info('k4name ' + jobname)

            # hier neue cname generierung ff
            cname = jobname
            # strip .xml-suffix:
            if cname.endswith('.xml'):
                cname = cname[:-4]

            cname = mangleQPSName(cname)
            # print "current: " + cmslocation + cname
            if cname[0] == '_':
                cname=cname[1:]

            # no duplicate filenames
            if cname in cnames:
                cname = cname + str(count)
            cnames.append(cname)

            # set extra metadata
            doc.metadata.append(
                ('http://namespaces.zeit.de/CMS/document', 'file-name', cname))
            doc.metadata.append(
                ('http://namespaces.zeit.de/CMS/document', 'export_cds', 'no'))

            # create the new resource
            logger.info('urlified ' + cname)

            # get infos for archive paths
            year = doc.getAttributeValue(DOC_NS, 'year')
            volume = doc.getAttributeValue(DOC_NS, 'volume')
            print_ressort = doc.getAttributeValue(PRINT_NS, 'ressort')

            product_id = doc.get_product_id(product_id_in, k4_filename)
            logging.info("ProductId: "+ product_id)

            cms_paths = []
            if year and volume and print_ressort:
                print_ressort = mangleQPSName(print_ressort).lower()
                cms_paths.append(IMPORT_ROOT + '%s/%s/%s/%s/%s' % (
                    product_id, year, volume, print_ressort, cname))
                cms_paths.append(IMPORT_ROOT_IN + '%s/%s/%s/%s/%s' % (
                    product_id, year, volume, print_ressort, cname))
                logging.info(
                    '%s, %s, %s, %s', product_id, year, volume, print_ressort)
                prepareColl(connector, product_id, year, volume, print_ressort)
            else:
                sys.exit('ERROR: Metadaten fehlen!!')

            # add attributes to output document
            doc.addAttributesToDoc(product_id, year, volume, cname)
            # get the new doc as XML String
            new_xml = doc.to_string()

            logger.info("SPEICHERN ins CMS ...")
            for cms_id in cms_paths:
                check_resource = None
                try:
                    check_resource= connector[cms_id]
                except KeyError, e:
                    logger.info(e)

                if check_resource:
                    logger.info(cms_id + "... wurde _nicht_ neu importiert")
                    continue

                if new_xml:
                    res = Resource(
                        cms_id, cname, 'article', StringIO.StringIO(new_xml),
                        contentType='text/xml')
                    for prop in doc.metadata:  # add metadata
                        prop_val = re.sub(r'\&', ' + ', prop[2])
                        res.properties[(prop[1], prop[0])] = (prop_val)
                    connector.add(res)
                    logger.info("GESPEICHERT: %s" % (cms_id,))
            count = count +1
            logger.info("IMPORT Dokument \"%s\" fertig\n" % (cname))

        except Exception, e:
            logger.exception(e)
            continue

    if count > 0:
        moveExportToArchive(input_dir)  # moves xml files to local archive
    else:
        logger.info('No documents to import found "%s" !' % input_dir)


def getConnector(dev=None):
    if dev:
        import zeit.connector.mock
        connector = zeit.connector.mock.Connector('http://xml.zeit.de/')
        # add mock config
        conf_id = 'http://xml.zeit.de/forms/importexport.xml'
        conf_file = open(os.path.dirname(__file__)
                         + '/testdocs/ipool/importexport.xml')
        res = Resource(
            conf_id, 'importexport.xml', 'text', conf_file,
            contentType='text/xml')
        connector.add(res)
    else:
        import zeit.connector.connector
        connector = zeit.connector.connector.Connector(
            {'default': CONNECTOR_URL})
    return connector


def main(**kwargs):
    # XXX Refactor and do  not rely on globals here
    for name, value in kwargs.items():
        globals()[name] = value

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-i", "--indir", dest="input_dir",
                      help="directory with the k4 export files")
    parser.add_option("-p", "--productid", dest="product_id",
                      help="product id to be used with every article")
    parser.add_option("-l", "--log", dest="logfile",
                      help="logfile for errors")
    parser.add_option("-d", "--dev", action="store_true", dest="dev",
                      help="use dev connector")

    (options, args) = parser.parse_args()

    if not options.input_dir:
        options.input_dir = K4_EXPORT_DIR
        logger.info('using default indir %s' % options.input_dir)

    if 'LOGFILE' in globals():
        add_file_logging(logger, globals()['LOGFILE'])

    if options.logfile:
        add_file_logging(logger, options.logfile)

    try:
        logger.info("Import: " + options.input_dir + " to: " + IMPORT_ROOT)
        connector = getConnector(options.dev)
        run_dir(connector, options.input_dir, options.product_id)
    except KeyboardInterrupt:
        logger.info('SCRIPT STOPPED')
        sys.exit()
    except Exception, e:
        logger.exception(e)
