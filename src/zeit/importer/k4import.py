import sys
import os
from optparse import OptionParser
import logging
from zeit.importer import add_file_logging


logger = logging.getLogger(__name__) 

QUARK_NS = 'http://namespaces.zeit.de/QPS/attributes'
DOC_NS = 'http://namespaces.zeit.de/CMS/document'
PRINT_NS = 'http://namespaces.zeit.de/CMS/print'
WORKFLOW_NS = 'http://namespaces.zeit.de/CMS/workflow'
CONNECTOR_URL = 'http://zip6.zeit.de:9000/cms/'
CMS_ROOT='http://xml.zeit.de/'
IMPORT_ROOT = CMS_ROOT+'archiv-wf/archiv/'
IMPORT_ROOT_IN = CMS_ROOT+'archiv-wf/archiv-in/'

K4_EXPORT_DIR = '/var/cms/import/k4incoming/'
K4_ARCHIVE_DIR = '/var/cms/import/old/'

products = {
        'ZEI': 'Die Zeit',
        'ZMLB': 'Zeit Magazin',
        'TEST': 'Test/Development',
        'ZTCS' : 'Zeit Campus',
        'ZTWI' : 'Zeit Wissen',
        'ZEDE' : 'Zeit.de',
        'ZTGS' : 'Zeit Geschichte',
        'tdb' : 'Zeit Schweiz',
        'tbd' : 'Zeit Oesterreich',
        'KINZ': 'Kinderzeit Magazin',
         }

product_map = {
        '1133533088' : 'ZEI',
        '104518514'  : 'ZMLB',
        '1153836019' : 'ZTCS',
        '1160501943' : 'ZTWI',
        '1144226254' : 'ZTGS',
         }

def run_dir(input_dir, product_id):

    if not os.path.isdir(input_dir):
        raise IOError("No such directory '%s'" % (input_dir,))

    imported_docs = 0
    
    k4_files = os.listdir(input_dir)
    
    for(k4_filename, k4_filepath) in [ (f, os.path.join(input_dir, f)) for f in k4_files ]:
        ## skip dirs
        if (os.path.isdir(k4_filepath)):
           continue

        logger.info(k4_filename)

def main():
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-i", "--indir", dest="input_dir",
                      help="directory with the k4 export files")
    parser.add_option("-p", "--productid", dest="product_id",
                      help="Productid")
    parser.add_option("-l", "--log", dest="logfile",
                      help="logfile for errors")

    (options, args) = parser.parse_args()

    if not options.input_dir:
        options.input_dir = K4_EXPORT_DIR
        logger.info('using default indir %s' % options.input_dir)

    if options.logfile:
        logging.error('TODO logfile handling')
        add_file_logging(logger, options.logfile) 

    try:
        logger.info("Import: " +  options.input_dir + " to: " +  os.path.normpath(CMS_ROOT+IMPORT_ROOT))
        run_dir(options.input_dir, options.product_id)        
    except KeyboardInterrupt,e:
        logger.info('SCRIPT STOPPED')
        sys.exit()
    except Exception, e:
        logger.exception(e)
