# -*- coding: utf-8 -*-
"""
    test_facebook_login

    Test the facebook login

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
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
from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
from trytond.modules import register_classes
register_classes()
from nereid.testing import testing_proxy, TestCase
from trytond.transaction import Transaction
from trytond.pool import Pool

_def = []
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


class TestFacebookAuth(TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestFacebookAuth, cls).setUpClass()
        # Install module
        testing_proxy.install_module('nereid_auth_facebook')

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            country_obj = Pool().get('country.country')
            currency_obj = Pool().get('currency.currency')

            company = testing_proxy.create_company('Test Company')
            testing_proxy.set_company_for_user(1, company)

            cls.guest_user = testing_proxy.create_guest_user(company=company)
            cls.regd_user_id = testing_proxy.create_user_party(
                'Registered User', 'email@example.com', 'password', company
            )

            cls.available_countries = country_obj.search([], limit=5)
            cls.available_currencies = currency_obj.search([
                ('code', '=', 'USD')
            ])

            cls.site = testing_proxy.create_site(
                'localhost',
                countries = [('set', cls.available_countries)],
                currencies = [('set', cls.available_currencies)],
                application_user = 1,
                guest_user = cls.guest_user,
            )

            testing_proxy.create_template(
                'home.jinja', '{{ get_flashed_messages() }}', cls.site
            )
            testing_proxy.create_template(
                'login.jinja',
                '{{ login_form.errors }} {{ get_flashed_messages() }}',
                cls.site
            )
            txn.cursor.commit()

    def get_app(self, **options):
        return testing_proxy.make_app(SITE='localhost', **options)

    def setUp(self):
        self.nereid_user_obj = testing_proxy.pool.get('nereid.user')
        self.website_obj = testing_proxy.pool.get('nereid.website')

    def test_0010_login(self):
        """
        Check for login with the next argument without API settings
        """
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
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            self.website_obj.write(self.site, {
                'facebook_app_id': get_from_env('FACEBOOK_APP_ID'),
                'facebook_app_secret': get_from_env('FACEBOOK_APP_SECRET'),
            })
            txn.cursor.commit()

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
