# -*- coding: utf-8 -*-
"""
    user

    Facebook based user authentication code

    :copyright: (c) 2012-2013 by Openlabs Technologies & Consulting (P) LTD
    :license: GPLv3, see LICENSE for more details.
"""
from nereid import url_for, flash, redirect, current_app
from nereid.globals import session, request
from nereid.signals import login, failed_login
from flask_oauth import OAuth
from trytond.model import fields
from trytond.pool import PoolMeta

from .i18n import _


__all__ = ['Website', 'NereidUser']
__metaclass__ = PoolMeta


class Website:
    """Add Globalcollect settings"""
    __name__ = "nereid.website"

    facebook_app_id = fields.Char("Facebook App ID")
    facebook_app_secret = fields.Char("Facebook App Secret")

    def get_facebook_oauth_client(self):
        """
        Returns a instance of WebCollect
        """
        if not all([self.facebook_app_id, self.facebook_app_secret]):
            current_app.logger.error("Facebook api settings are missing")
            flash(_("Facebook login is not available at the moment"))
            return None

        oauth = OAuth()
        facebook = oauth.remote_app(
            'facebook',
            base_url='https://graph.facebook.com/',
            request_token_url=None,
            access_token_url='/oauth/access_token',
            authorize_url='https://www.facebook.com/dialog/oauth',
            consumer_key=self.facebook_app_id,
            consumer_secret=self.facebook_app_secret,
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


class NereidUser:
    "Nereid User"
    __name__ = "nereid.user"

    facebook_id = fields.Char('Facebook ID')

    @classmethod
    def facebook_login(cls):
        """The URL to which a new request to authenticate to facebook begins
        Usually issues a redirect.
        """
        facebook = request.nereid_website.get_facebook_oauth_client()
        if facebook is None:
            return redirect(
                request.referrer or url_for('nereid.website.login')
            )
        return facebook.authorize(
            callback=url_for(
                'nereid.user.facebook_authorized_login',
                next=request.args.get('next') or request.referrer or None,
                _external=True
            )
        )

    @classmethod
    def facebook_authorized_login(cls):
        """Authorized handler to which facebook will redirect the user to
        after the login attempt is made.
        """
        facebook = request.nereid_website.get_facebook_oauth_client()
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
            flash(
                _("We cannot talk to facebook at this time. Please try again")
            )
            return redirect(
                request.referrer or url_for('nereid.website.login')
            )

        if data is None:
            flash(_(
                "Access was denied to facebook: %(reason)s",
                reason=request.args['error_reason']
            ))
            failed_login.send(form=data)
            return redirect(url_for('nereid.website.login'))

        # Write the oauth token to the session
        session['facebook_oauth_token'] = (data['access_token'], '')

        # Find the information from facebook
        me = facebook.get('/me')

        # Find the user
        users = cls.search([
            ('email', '=', me.data['email']),
            ('company', '=', request.nereid_website.company.id),
        ])
        if not users:
            current_app.logger.debug(
                "No FB user with email %s" % me.data['email']
            )
            current_app.logger.debug(
                "Registering new user %s" % me.data['name']
            )
            user, = cls.create([{
                'name': me.data['name'],
                'display_name': me.data['name'],
                'email': me.data['email'],
                'facebook_id': me.data['id'],
                'addresses': False,
            }])
            flash(
                _('Thanks for registering with us using facebook')
            )
        else:
            user, = users

        # Add the user to session and trigger signals
        session['user'] = user.id
        if not user.facebook_id:
            # if the user has no facebook id save it
            cls.write([user], {'facebook_id': me.data['id']})
        flash(_(
            "You are now logged in. Welcome %(name)s", name=user.display_name
        ))
        login.send()
        if request.is_xhr:
            return 'OK'
        return redirect(
            request.values.get(
                'next', url_for('nereid.website.home')
            )
        )
