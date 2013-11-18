# -*- coding: utf-8 -*-
"""
    test_facebook_login

    Test the facebook login

    :copyright: (c) 2012-2013 by Openlabs Technologies & Consulting (P) LTD
    :license: GPLv3, see LICENSE for more details.
"""
import os
import unittest
import BaseHTTPServer
import urlparse
import threading
import webbrowser
from StringIO import StringIO

from lxml import etree

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from nereid.testing import NereidTestCase

_def = []


def get_from_env(key):
    """
    Find a value from environ or return the default if specified
    If the return value is not specified then raise an error if
    the value is NOT in the environment
    """
    try:
        return os.environ[key]
    except KeyError:
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
        self.wfile.write(
            "Hola, go back to your terminal window to see results"
        )
        return


class TestFacebookAuth(NereidTestCase):
    "Test Facebook Authenticated login"

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid_auth_facebook')

        self.Company = POOL.get('company.company')
        self.Country = POOL.get('country.country')
        self.Currency = POOL.get('currency.currency')
        self.NereidUser = POOL.get('nereid.user')
        self.UrlMap = POOL.get('nereid.url_map')
        self.Language = POOL.get('ir.lang')
        self.Website = POOL.get('nereid.website')
        self.Party = POOL.get('party.party')
        self.Locale = POOL.get('nereid.website.locale')

    def setup_defaults(self):
        """
        Setup defaults
        """
        usd, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])
        party1, = self.Party.create([{
            'name': 'Openlabs'
        }])
        company, = self.Company.create([{
            'party': party1.id,
            'currency': usd.id
        }])
        party2, = self.Party.create([{
            'name': 'Guest User'
        }])
        guest_user, = self.NereidUser.create([{
            'party': party2.id,
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': company.id,
        }])

        party3, = self.Party.create([{
            'name': 'Registered User'
        }])
        self.NereidUser.create([{
            'party': party3.id,
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': company.id,
        }])
        url_map, = self.UrlMap.search([], limit=1)
        en_us, = self.Language.search([('code', '=', 'en_US')])
        self.locale_en_us, = self.Locale.create([{
            'code': 'en_US',
            'language': en_us.id,
            'currency': usd.id,
        }])
        # When running this module, add site url's name in the app created
        # using facebook
        site, = self.Website.create([{
            'name': 'localhost',
            'url_map': url_map.id,
            'company': company.id,
            'application_user': USER,
            'default_locale': self.locale_en_us.id,
            'guest_user': guest_user.id,
        }])
        self.templates = {
            'home.jinja': '{{ get_flashed_messages() }}',
            'login.jinja':
                '{{ login_form.errors }} {{ get_flashed_messages() }}',
        }
        return {
            'site': site
        }

    def get_template_source(self, name):
        """
        Return templates
        """
        return self.templates.get(name)

    def test_0010_login(self):
        """
        Check for login with the next argument without API settings
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/auth/facebook?next=/')
                self.assertEqual(response.status_code, 302)

            # Redirect to the home page since
            self.assertTrue(
                '<a href="/login">/login</a>' in
                response.data
            )
            response = c.get('/')
            self.assertTrue(
                'Facebook login is not available at the moment' in
                response.data
            )

    def test_0020_login(self):
        """
        Login with facebook settings
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            data = self.setup_defaults()
            app = self.get_app()
            self.Website.write([data['site']], {
                'facebook_app_id': get_from_env('FACEBOOK_APP_ID'),
                'facebook_app_secret': get_from_env('FACEBOOK_APP_SECRET'),
            })

            with app.test_client() as c:
                response = c.get('/auth/facebook?next=/en_US')
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    'https://www.facebook.com/dialog/oauth' in response.data
                )

            # send the user to the webbrowser and wait for a redirect
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(response.data), parser)
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
