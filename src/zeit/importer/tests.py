from zope.testing import doctest
import pkg_resources
import unittest
import zeit.connector.mock
import zeit.connector.resource

settings = {
    'connector_url': 'mocked',
    'k4_export_dir': '/var/cms/import/k4incoming/',
    'k4_archive_dir': '/var/cms/import/old/',
    'import_root': 'http://xml.zeit.de/archiv-wf/archiv/',
    'import_root_in': 'http://xml.zeit.de/archiv-wf/archiv-in/',
    'ipool_conf': 'http://xml.zeit.de/forms/importexport.xml',
}


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocFileSuite(
        'README.txt',
        optionflags=doctest.ELLIPSIS + doctest.REPORT_NDIFF,
    ))
    return suite


def getConnector():
    connector = zeit.connector.mock.Connector('http://xml.zeit.de/')
    res = zeit.connector.resource.Resource(
        'http://xml.zeit.de/forms/importexport.xml', 'importexport.xml',
        'text', pkg_resources.resource_stream(
            __name__, '/testdocs/ipool/importexport.xml'),
        contentType='text/xml')
    connector.add(res)
    return connector
