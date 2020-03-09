from zeit.importer.article import Article
import os.path
import pkg_resources
import unittest
import zeit.connector.mock
import zeit.connector.resource
import zeit.importer.interfaces
import zeit.importer.k4import
import zope.component


settings = {
    'connector_url': 'mocked',
    'k4_export_dir': '/var/cms/import/k4incoming/',
    'k4_archive_dir': '/var/cms/import/old/',
    'k4_highres_dir': os.path.dirname(__file__) + '/testdocs/',
    'highres_sample_size': 4,
    'highres_diff_cutoff': 0.1,
    'import_root': 'http://xml.zeit.de/archiv-wf/archiv/',
    'import_root_in': 'http://xml.zeit.de/archiv-wf/archiv-in/',
    'import_config': 'http://xml.zeit.de/forms/importexport.xml',
    'ressortmap': 'http://xml.zeit.de/forms/printimport-ressortmap.xml',
    'access_source': 'http://xml.zeit.de/work/data/access.xml',
    'access_override_value': 'registration'
}


def getConnector():
    connector = zeit.connector.mock.Connector('http://xml.zeit.de/')
    for name in ['importexport.xml', 'printimport-ressortmap.xml']:
        connector.add(zeit.connector.resource.Resource(
            'http://xml.zeit.de/forms/%s' % name, name,
            'text', pkg_resources.resource_stream(
                __name__, 'testdocs/ipool/%s' % name),
            contentType='text/xml'))
    connector.add(zeit.connector.resource.Resource(
        settings['access_source'], 'access_source',
        'text', pkg_resources.resource_stream(
            __name__, 'testdocs/ipool/access.xml'),
        contentType='text/xml'))
    return connector


class TestCase(unittest.TestCase):

    def _get_doc(self, filename='Sp_te_Flucht_89.xml'):
        return Article(
            os.path.dirname(__file__) + '/testdocs/{}'.format(filename))

    def setUp(self):
        self.connector = getConnector()
        zope.component.provideUtility(self.connector)
        zope.component.provideUtility(
            settings, zeit.importer.interfaces.ISettings)
        zeit.importer.k4import._configure_from_dav_xml()
        self.settings = zope.component.getUtility(
            zeit.importer.interfaces.ISettings)
