# -*- coding: utf-8 -*-
"""
    test_facebook_login

    Test view and depends

    :copyright: (c) 2013-2015 by Openlabs Technologies & Consulting (P) LTD
    :license: GPLv3, see LICENSE for more details.
"""
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends


class TestViewAndDepends(unittest.TestCase):
    '''
    Test View and Depends
    '''
    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('nereid_auth_facebook')

    def test_0005_test_view(self):
        """
        Test the view
        """
        test_view('nereid_auth_facebook')

    def test_0006_test_depends(self):
        """
        Test Depends
        """
        test_depends()


def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestViewAndDepends)
    )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
