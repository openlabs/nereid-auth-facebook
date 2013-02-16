# -*- coding: utf-8 -*-
"""
    test_facebook_login

    Test the facebook login

    :copyright: (c) 2012-2013 by Openlabs Technologies & Consulting (P) LTD
    :license: GPLv3, see LICENSE for more details.
"""
import os
import unittest2 as unittest
import BaseHTTPServer
import urlparse
import threading
import webbrowser
from StringIO import StringIO
from lxml import etree

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT, \
    test_view, test_depends
from nereid.testing import NereidTestCase
from trytond.transaction import Transaction

def get_from_env(key):
    """
    Find a value from environ or return the default if specified
    If the return value is not specified then raise an error if
    the value is NOT in the environment
    """
    try:
        return os.environ[key]
    except KeyError, error:
        raise Exception("%s is not set in environ" % key)

REQUEST_RECEIVED = None


class RequestStack(threading.local):
    "Stack for storing the responses from async server"
    items = []

_request_ctx_stack = RequestStack()


class FacebookHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    "Special Class to handle the POST from Facebook"

    def do_GET(self):
        "Handle POST"
        parsed_path = urlparse.urlparse(self.path)
        print "parsed_path", parsed_path
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Hola, go back to your terminal window to see results")
        return


class TestFacebookAuth(NereidTestCase):

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid_auth_facebook')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.nereid_website_obj = POOL.get('nereid.website')
        self.country_obj = POOL.get('country.country')
        self.currency_obj = POOL.get('currency.currency')
        self.company_obj = POOL.get('company.company')
        self.url_map_obj = POOL.get('nereid.url_map')
        self.language_obj = POOL.get('ir.lang')

    def setup_defaults(self):
        """
        Setup the defaults
        """
        usd = self.currency_obj.create({
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        })
        company_id = self.company_obj.create({
            'name': 'Openlabs',
            'currency': usd
        })
        guest_user = self.nereid_user_obj.create({
            'name': 'Guest User',
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': company_id,
        })
        self.registered_user_id = self.nereid_user_obj.create({
            'name': 'Registered User',
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': company_id,
        })
        url_map_id, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.site = self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': company_id,
            'application_user': USER,
            'default_language': en_us,
            'guest_user': guest_user,
        })

    def get_template_source(self, name):
        """
        Return templates
        """
        self.templates = {
            'localhost/home.jinja': '{{ get_flashed_messages() }}',
            'localhost/login.jinja':
                '{{ login_form.errors }} {{ get_flashed_messages() }}'
        }
        return self.templates.get(name)

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

    def test_0010_login(self):
        """
        Check for login with the next argument without API settings
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/en_US/auth/facebook?next=/en_US')
                self.assertEqual(response.status_code, 302)
                # Redirect to the home page since
                self.assertTrue(
                    '<a href="/en_US/login">/en_US/login</a>' in response.data
                )
                rv = c.get('/')
                self.assertTrue(
                    'Facebook login is not available at the moment' in rv.data
                )

    def test_0020_login(self):
        """
        Login with facebook settings
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            self.nereid_website_obj.write(self.site, {
                'facebook_app_id': get_from_env('FACEBOOK_APP_ID'),
                'facebook_app_secret': get_from_env('FACEBOOK_APP_SECRET'),
            })

            app = self.get_app()
            with app.test_client() as c:
                response = c.get('/en_US/auth/facebook?next=/en_US')
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    'https://www.facebook.com/dialog/oauth' in response.data
                )
                # send the user to the webbrowser and wait for a redirect
                parser = etree.HTMLParser()
                tree   = etree.parse(StringIO(response.data), parser)
                webbrowser.open(tree.xpath('//p/a')[0].values()[0])


def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestFacebookAuth)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
