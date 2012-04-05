# -*- coding: utf-8 -*-
"""
    user

    Facebook based user authentication code

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
from nereid import url_for, flash, redirect, current_app
from nereid.globals import session, request
from nereid.signals import login, failed_login
from flaskext.oauth import OAuth
from trytond.model import ModelSQL, ModelView, fields

from .i18n import _


class Website(ModelSQL, ModelView):
    """Add Globalcollect settings"""
    _name = "nereid.website"

    facebook_app_id = fields.Char("Facebook App ID")
    facebook_app_secret = fields.Char("Facebook App Secret")

    def get_facebook_oauth_client(self, site=None):
        """Returns a instance of WebCollect

        :param site: Browserecord of the website, If not specified, it will be
                     guessed from the request context
        """
        if site is None:
            site = request.nereid_website

        if not all([site.facebook_app_id, site.facebook_app_secret]):
            current_app.logger.error("Facebook api settings are missing")
            flash(_("Facebook login is not available at the moment"))
            return None

        oauth = OAuth()
        facebook = oauth.remote_app('facebook',
            base_url='https://graph.facebook.com/',
            request_token_url=None,
            access_token_url='/oauth/access_token',
            authorize_url='https://www.facebook.com/dialog/oauth',
            consumer_key=site.facebook_app_id,
            consumer_secret=site.facebook_app_secret,
            request_token_params={'scope': 'email'}
        )
        facebook.tokengetter_func = lambda *a: session.get(
                'facebook_oauth_token'
        )
        return facebook

    def _user_status(self):
        """
        Add facebook_id to the user_status if the user is logged in
        """
        rv = super(Website, self)._user_status()
        if not request.is_guest_user and request.nereid_user.facebook_id:
            rv['facebook_id'] = request.nereid_user.facebook_id
        return rv

Website()


class NereidUser(ModelSQL, ModelView):
    "Nereid User"
    _name = "nereid.user"

    facebook_id = fields.Char('Facebook ID')

    def facebook_login(self):
        """The URL to which a new request to authenticate to facebook begins
        Usually issues a redirect.
        """
        website_obj = self.pool.get('nereid.website')

        facebook = website_obj.get_facebook_oauth_client()
        if facebook is None:
            return redirect(
                request.referrer or url_for('nereid.website.login')
            )
        return facebook.authorize(
            callback = url_for('nereid.user.facebook_authorized_login',
                next = request.args.get('next') or request.referrer or None,
                _external = True
            )
        )

    def facebook_authorized_login(self):
        """Authorized handler to which facebook will redirect the user to
        after the login attempt is made.
        """
        website_obj = self.pool.get('nereid.website')

        facebook = website_obj.get_facebook_oauth_client()
        if facebook is None:
            return redirect(
                request.referrer or url_for('nereid.website.login')
            )

        try:
            if 'oauth_verifier' in request.args:
                data = facebook.handle_oauth1_response()
            elif 'code' in request.args:
                data = facebook.handle_oauth2_response()
            else:
                data = facebook.handle_unknown_response()
            facebook.free_request_token()
        except Exception, exc:
            current_app.logger.error("Facebook login failed", exc)
            flash(_("We cannot talk to facebook at this time. Please try again"))
            return redirect(
                request.referrer or url_for('nereid.website.login')
            )

        if data is None:
            flash(
                _("Access was denied to facebook: %(reason)s",
                reason=request.args['error_reason'])
            )
            failed_login.send(self, form=data)
            return redirect(url_for('nereid.website.login'))

        # Write the oauth token to the session
        session['facebook_oauth_token'] = (data['access_token'], '')

        # Find the information from facebook
        me = facebook.get('/me')

        # Find the user
        user_ids = self.search([
            ('email', '=', me.data['email']),
            ('company', '=', request.nereid_website.company.id),
        ])
        if not user_ids:
            current_app.logger.debug(
                "No FB user with email %s" % me.data['email']
            )
            current_app.logger.debug(
                "Registering new user %s" % me.data['name']
            )
            user_id = self.create({
                'name': me.data['name'],
                'email': me.data['email'],
                'facebook_id': me.data['id'],
                'addresses': False,
            })
            flash(
                _('Thanks for registering with us using facebook')
            )
        else:
            user_id, = user_ids

        # Add the user to session and trigger signals
        session['user'] = user_id
        user = self.browse(user_id)
        if not user.facebook_id:
            # if the user has no facebook id save it
            self.write(user_id, {'facebook_id': me.data['id']})
        flash(_("You are now logged in. Welcome %(name)s",
                    name=user.name))
        login.send(self)
        if request.is_xhr:
            return 'OK'
        return redirect(
            request.values.get(
                'next', url_for('nereid.website.home')
            )
        )


NereidUser()
