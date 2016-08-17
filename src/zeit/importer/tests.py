from zope.testing import doctest
import pkg_resources
import unittest
import zeit.connector.mock
import zeit.connector.resource


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
