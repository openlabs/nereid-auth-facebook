# -*- coding: utf-8 -*-
'''

    Test LinkedIn login

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details

'''
import unittest
import trytond.tests.test_tryton
from tests.test_view_depends import TestViewAndDepends
from test_facebook_login import TestFacebookAuth


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestViewAndDepends),
        unittest.TestLoader().loadTestsFromTestCase(TestFacebookAuth),
    ])
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
