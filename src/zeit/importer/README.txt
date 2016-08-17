>>> import zeit.importer.tests
>>> connector = zeit.importer.tests.getConnector()
>>> connector
<zeit.connector.mock.Connector object at 0x...>

Check for generating proper filenames, name ar in unicode

>>> from zeit.importer import k4import
>>> k4import.mangleQPSName('Streitgespr‰ch_Vitakasten'.decode('utf-8'))
'Streitgespraech-Vitakasten'
>>> k4import.mangleQPSName('Kˆpfe der Zeit'.decode('utf-8'))
'Koepfe-der-Zeit'
>>> k4import.mangleQPSName('÷-Scharinger'.decode('utf-8'))
'Oe-Scharinger'
>>> k4import.mangleQPSName('HfjS_Portr‰t'.decode('utf-8'))
'HfjS-Portraet'


Remove ugly print layout

>>> from zeit.importer.article import sanitizeDoc
>>> xml = "<p>E</p>\r\n<p>in Test"
>>> sanitizeDoc(xml)
'<p>Ein Test'

Convert k4.xml to zeit-article.xml

>>> import os.path
>>> from zeit.importer.article import transform_k4
>>> new_doc = transform_k4(os.path.dirname(__file__)+'/testdocs/Sp_te_Flucht_89.xml')
>>> print new_doc
<?xml version="1.0" encoding="UTF-8"?>
<article>
  <head>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="status">import</attribute>
...

We need the settings for infopool

>>> from zeit.importer.ipoolconfig import IPoolConfig
>>> ipool = IPoolConfig( connector['http://xml.zeit.de/forms/importexport.xml'])

Check it:

>>> ipool.product_map['1153836019']
'ZTCS'
>>> ipool.products['ZMLB']
'ZEIT Magazin'


now with the infopool data and the new doc, we will treat them right

>>> from zeit.importer.article import TransformedArticle
>>> doc = TransformedArticle(new_doc, ipool)
>>> doc
<zeit.importer.article.TransformedArticle object at 0...>

we have metadata

>>> print doc.metadata
[('http://namespaces.zeit.de/CMS/workflow', 'status', 'import')...


get a single value from the metadata

>>> jobname = doc.getAttributeValue('http://namespaces.zeit.de/CMS/document','jobname')
>>> jobname
u'Sp\u2030te Flucht 89'

check product id for DACH

>>> doc.get_product_id(None, 'A-Test')
'ZEOE'
>>> doc.get_product_id(None, 'A_Test')
'ZEOE'
>>> doc.get_product_id(None, 'CH-Teäst')
'ZECH'
>>> doc.get_product_id(None, 'CH_Teäst')
'ZECH'
>>> doc.get_product_id(None, 'ACH-Test')
'ZEI'
>>> doc.get_product_id(None, 'ACH_Test')
'ZEI'
>>> doc.get_product_id(None, 'S-Test')
'ZESA'
>>> doc.get_product_id(None, 'S_Test')
'ZESA'

get publication id

>>> publication_id = doc.getAttributeValue('http://namespaces.zeit.de/CMS/print','publication-id')
>>> product_id = ipool.product_map.get(publication_id)
>>> product_id
'ZEI'

Build collections for import

>>> year = doc.getAttributeValue('http://namespaces.zeit.de/CMS/document','year')
>>> volume = doc.getAttributeValue('http://namespaces.zeit.de/CMS/document','volume')
>>> print_ressort = doc.getAttributeValue('http://namespaces.zeit.de/CMS/print', 'ressort')
>>> print_ressort = k4import.mangleQPSName(print_ressort).lower()
>>> k4import.prepareColl(connector, product_id, year, volume, print_ressort)
>>> connector['http://xml.zeit.de/archiv-wf/archiv/ZEI/2009/40/feuilleton'].type
'collection'
>>> connector['http://xml.zeit.de/archiv-wf/archiv-in/ZEI/2009/40/feuilleton'].type
'collection'

Add additional attributes to head/attributes

>>> cname = k4import.mangleQPSName(jobname)
>>> doc.addAttributesToDoc(product_id, year, volume, cname)
>>> new_xml = doc.to_string()
>>> print new_xml
<?xml version='1.0' encoding='utf-8'?>
<article>
  <head>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="status">import</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="ipad_template"/>
    <attribute ns="http://namespaces.zeit.de/CMS/print" name="article_id">254475</attribute>
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
    <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="product-name">DIE ZEIT</attribute>
    <attribute ns="http://namespaces.zeit.de/CMS/document" name="export_cds">no</attribute>
...
