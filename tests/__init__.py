# -*- coding: utf-8 -*-
"""
    __init__

    Test Suite for the BCI module

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest

import trytond.tests.test_tryton

from .test_facebook_login import TestFacebookAuth


def suite():
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestFacebookAuth)
    ])
    return test_suite
