import unittest
from zope.testing import doctest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocFileSuite(
        'README.txt',       
        'ipoolconfig.txt',
        optionflags=doctest.ELLIPSIS
        ))

    return suite
