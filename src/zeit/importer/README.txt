At first, we need a connector for our beloved importer.

>>> import zeit.connector.mock
>>> connector = zeit.connector.mock.Connector()
>>> connector
<zeit.connector.mock.Connector object at 0x...>

then we need a module which will do the work for us

>>> from zeit.importer import k4import
>>> k4import
<module 'zeit.importer.k4import'...>

Check for generating proper filenames, name ar in unicode

>>> k4import.mangleQPSName('Streitgespr‰ch_Vitakasten'.decode('utf-8'))
'Streitgespraech-Vitakasten'
>>> k4import.mangleQPSName('Kˆpfe der Zeit'.decode('utf-8'))
'Koepfe-der-Zeit'
>>> k4import.mangleQPSName('÷-Scharinger'.decode('utf-8'))
'Oe-Scharinger'
>>> k4import.mangleQPSName('HfjS_Portr‰t'.decode('utf-8'))
'HfjS-Portraet'

Remove ugly print layout 

>>> xml = "<p>E</p>\r\n<p>in Test"
>>> k4import.sanitizeDoc(xml)
'<p>Ein Test'

Convert k4.xml to zeit-article.xml

>>> import os.path
>>> new_doc = k4import.transform_k4(os.path.dirname(__file__)+'/testdocs/Sp_te_Flucht_89.xml')
>>> print new_doc
<?xml version="1.0" encoding="UTF-8"?>
<article>
  <head>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="status">import</attribute>
...

get the attributes from the new document

>>> metadata = k4import.getAttributesFromDoc(new_doc)
>>> metadata[3]
('http://namespaces.zeit.de/CMS/workflow', 'last-modified-by', 'import')

get a single value from the metadata

>>> jobname = k4import.getAttributeValue(metadata, 'http://namespaces.zeit.de/CMS/document','jobname')
>>> jobname
u'Sp\u2030te Flucht 89'

get publication id

>>> publication_id = k4import.getAttributeValue(metadata, 'http://namespaces.zeit.de/CMS/print','publication-id')
>>> product_id = k4import.product_map.get(publication_id)
>>> product_id
'ZEI'

Build collections for import 

>>> year = k4import.getAttributeValue(metadata, 'http://namespaces.zeit.de/CMS/document','year')
>>> volume = k4import.getAttributeValue(metadata, 'http://namespaces.zeit.de/CMS/document','volume')
>>> print_ressort = k4import.getAttributeValue(metadata, 'http://namespaces.zeit.de/CMS/print', 'ressort')
>>> print_ressort = k4import.mangleQPSName(print_ressort).lower()
>>> k4import.prepareColl(connector, product_id, year, volume, print_ressort)
>>> connector['http://xml.zeit.de/archiv-wf/archiv/ZEI/2009/40/feuilleton'].type
'collection'
>>> connector['http://xml.zeit.de/archiv-wf/archiv-in/ZEI/2009/40/feuilleton'].type
'collection'

Add additional attributes to head/attributes

>>> cname = k4import.mangleQPSName(jobname)
>>> new_doc = k4import.addAttributesToDoc(new_doc, product_id, year, volume, cname)
>>> new_xml = k4import.doc_to_string(new_doc)
>>> print new_xml
<?xml version='1.0' encoding='utf-8'?>
<article>
  <head>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="status">import</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="importsource">k4</attribute>
    ...
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="erscheint">24.09.2009</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="date_first_released">2009-09-24T06:00:00+00:00</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="copyrights">DIE ZEIT, 24.09.2009 Nr. 40</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="page">55-55</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="ressort">Kultur</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/print" name="ressort">Feuilleton</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="id">ZEI-2009-40-Spaete-Flucht-89</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="running-volume">ZEI-2009-40</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="product-id">ZEI</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="product-name">Die Zeit</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="export_cds">no</attribute>
...

