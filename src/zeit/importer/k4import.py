# -*- coding: utf-8 -*-
import sys
import os
import re
import logging
import StringIO
from optparse import OptionParser
from lxml import etree

from zeit.importer import add_file_logging
from zeit.connector.resource import Resource
import zeit.connector.connector



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
K4_STYLESHEET = os.path.dirname(__file__)+'/stylesheets/k4import.xslt'

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

p_pattern = re.compile('<p>([a-z0-9])</p>\s*<p>', re.M|re.I) # <p>V</p>

def sanitizeDoc(xml):
    '''
        cleans the doc from dirty k4markup
    '''
    xml = p_pattern.sub('<p>\\1', xml)
    return xml

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
    
def mangleQPSName(qps_name):
    #- [ ] ersetzt werden ä,ö,ü,ß in ae,oe,ue,ss
    #- [ ] ersetzt wird _ . : ; # + * / in -
    #- [ ] doppelte sonderzeichen entfernen
    #- [ ] der rest per regexp- alphabet
    #qps_name = qps_name.lower()
    qps_name = qps_name.encode('utf-8')
    qps_name = qps_name.replace("ƒ","Ae") #Ä
    qps_name = qps_name.replace("‹","Ue") #Ü
    qps_name = qps_name.replace("÷","Oe") #Ö
    qps_name = qps_name.replace("‰","ae") #ä
    qps_name = qps_name.replace("¸","ue") #ü
    qps_name = qps_name.replace("ˆ","oe") #ö
    qps_name = qps_name.replace("ﬂ","ss")
    qps_name = qps_name.replace("&","")
    qps_name = qps_name.replace("?","")
    qps_name = qps_name.strip('_- ')
    cname = re.compile('[\ \_.:;#+*/\']').sub('-', qps_name)
    cname = re.compile('[^A-Za-z0-9\-]').sub('', cname)
    #cname = mangleName(urllib.unquote_plus(cname))
    cname = re.compile('-+').sub('-', cname)
    return cname

def prepareColl(connector, product_id, year, volume, print_ressort):
    for d in [IMPORT_ROOT, IMPORT_ROOT_IN]:
        coll_path = d
        parts = [product_id, year, volume, print_ressort]
        for p in parts:
            coll_path = os.path.join(coll_path, p)
            coll_create = None
            try:
                test_coll= connector[coll_path]
            except KeyError, e:
                coll_create = True

            if coll_create:
                coll_name = os.path.basename(coll_path)
                col = Resource(coll_path,
                    coll_name,
                    'collection',
                    StringIO.StringIO(''))
                connector.add(col)
                logger.info("collection %s created" % coll_path)


def transform_k4(k4xml_path):    
    '''
        transforms k4xml to zeit article format
    '''
    if not os.path.isfile(k4xml_path):
        raise IOError('%s does not exists' % k4xml_path)

    xslt_doc = etree.parse(K4_STYLESHEET)
    transform = etree.XSLT(xslt_doc)

    doc = etree.parse(k4xml_path)
    result = transform(doc)

    return  result

def getAttributesFromDoc(doc):
    '''
        extract metadata from /head/attributes/attribute
    '''
    metas = doc.xpath('//head/attribute')  

    props = []
    if metas:
      for m in metas:
        ns = m.get('ns')
        name = m.get('name')
        value = m.text if m.text is not None else ''
        props.append((ns,name,value))

    return props

def getAttributeValue(metadata, ns, name):
    """
    extract single metadata value from dict
    """
    try:
        return [m[2] for m in metadata if m[0] == ns and m[1] == name][0]
    except:
        return None

def addAttributesToDoc(doc, product_id, year, volume, cname):
    '''
        adds additional attributes to the document head
    '''
    head = doc.xpath('//article/head')[0]
    attributes = [
        '<attribute ns="%s" name="id">%s-%s-%s-%s</attribute>' % (WORKFLOW_NS, product_id, year, volume, cname),
        '<attribute ns="%s" name="running-volume">%s-%s-%s</attribute>' % (WORKFLOW_NS, product_id, year, volume),
        '<attribute ns="%s" name="product-id">%s</attribute>' % (WORKFLOW_NS, product_id),
        '<attribute ns="%s" name="product-name">%s</attribute>' % (WORKFLOW_NS, products.get(product_id,'')),
        '<attribute ns="%s" name="export_cds">%s</attribute>' % (DOC_NS,'no')
    ]
    for attr in attributes:
        head.append(etree.fromstring(attr))
    return doc

def doc_to_string(doc):
    """
        serializes xmldoc-object to string
    """
    indent(doc.getroot())
    xml = etree.tostring(doc, encoding="utf-8", xml_declaration=True)
    xml = sanitizeDoc(xml) #<p>V</p> etc
    return xml

def run_dir(input_dir, product_id):

    if not os.path.isdir(input_dir):
        raise IOError("No such directory '%s'" % (input_dir,))

    imported_docs = 0
    cnames = []
    connector = getConnector()

    k4_files = os.listdir(input_dir)
    for(k4_filename, k4_filepath) in [ (f, os.path.join(input_dir, f)) for f in k4_files ]:
        try:
        
            ## skip dirs
            if (os.path.isdir(k4_filepath)):
                continue

            logger.info('**** STARTING %s ****' % k4_filename)
            new_doc = transform_k4(k4_filepath)

            # get metadata
            metadata = getAttributesFromDoc(new_doc)

            # get original name
            jobname = getAttributeValue(metadata, DOC_NS,'jobname')
            if not jobname:
                raise Exception("Original name not found '%s'" % k4_filepath)

            logger.info('k4name '+jobname)

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
            metadata.append(('http://namespaces.zeit.de/CMS/document','file-name',cname))
            metadata.append(('http://namespaces.zeit.de/CMS/document','export_cds','no'))   

            logger.info('urlified '+cname)

            # get infos for archive paths
            year = getAttributeValue(metadata, DOC_NS,'year')
            volume = getAttributeValue(metadata, DOC_NS,'volume')
            print_ressort = getAttributeValue(metadata, PRINT_NS, 'ressort')
        
            if product_id is None:
                # no product_id was given as command line argument
                # get publciation-id for print_ressort
                publication_id = getAttributeValue(metadata, PRINT_NS,'publication-id')
                if not publication_id:
                    raise "PublicationId not found '%s%s'" % (dirname, file[0])

                # detect the Produktid
                product_id = product_map.get(publication_id)
                if not product_id:
                    print 'PublicationId ', publication_id, '>>>>> kein Produktmapping moeglich.'
                    continue

            logging.info("ProductId: "+ product_id)

            cms_paths = []
            if year and volume and print_ressort:
                print_ressort = mangleQPSName(print_ressort).lower()
                cms_paths.append(IMPORT_ROOT + '%s/%s/%s/%s/%s' % (product_id, year, volume, print_ressort, cname))
                cms_paths.append(IMPORT_ROOT_IN + '%s/%s/%s/%s/%s' % (product_id, year, volume, print_ressort,cname))
                logging.info('%s, %s, %s, %s' % (product_id, year, volume, print_ressort))
                prepareColl(connector, product_id, year, volume, print_ressort)
            else:
                sys.exit('ERROR: Metadaten fehlen!!')

            # add attributes to output document
            new_doc = addAttributesToDoc(new_doc, product_id, year, volume, cname)
          
            new_xml = doc_to_string(new_doc)

            logger.info("SPEICHERN ins CMS ...")
            for cms_id in cms_paths:
                check_resource = None                
                try:
                    check_resource= connector[cms_id]#CMSClient.CMS.Resource(cmslocation + cname, logger=logger)
                except KeyError, e:
                    logger.info(e)

                if check_resource:
                    logger.info(cms_id + "... wurde _nicht_ neu importiert")
                    continue

                if new_xml:
                    res = Resource( cms_id,
                        cname,
                        'article',
                        StringIO.StringIO(new_xml),
                        contentType = 'text/xml')
                    for prop in metadata: # add metadata
                        prop_val = re.sub(r'\&','+',prop[2])
                        res.properties[(prop[1],prop[0])] = (prop_val)
                    connector.add(res)
                    logger.info("GESPEICHERT: %s" % (cms_id,))
            logger.info("IMPORT Dokument \"%s\" fertig\n" % (cname))

        except Exception, e:
            logger.exception(e)
            sys.exit()
            continue        

def getConnector():
    import zeit.connector.mock
    connector = zeit.connector.mock.Connector()
    #connector = zeit.connector.connector.Connector({'default': CONNECTOR_URL})
    return connector    

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
        add_file_logging(logger, options.logfile) 

    try:
        logger.info("Import: " +  options.input_dir + " to: " +  os.path.normpath(CMS_ROOT+IMPORT_ROOT))
        run_dir(options.input_dir, options.product_id)        
    except KeyboardInterrupt,e:
        logger.info('SCRIPT STOPPED')
        sys.exit()
    except Exception, e:
        logger.exception(e)
