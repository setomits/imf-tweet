#-*- coding: utf-8 -*-

import logging
import os

from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.ext.webapp import template

from google.appengine.api import memcache, taskqueue
from google.appengine.ext import webapp

from appengine_utilities.sessions import Session
import tweepy

from models import UserInfo

DELAYS = [1, 3, 5, 10, 30, 60]

##
def _login_user(handler):
    handler.session = Session()
    twitter_id = handler.session.get('twitter_id')

    return UserInfo.all().filter('twitter_id =', twitter_id).get()


def _render(handler, tname, values = {}):
    tmplpath = os.path.join(os.path.dirname(__file__),
                            'templates/' + tname)

    _ua = handler.request.environ['HTTP_USER_AGENT'].lower()
    for s in ('iphone', 'android', 'docomo', 'softbank'):
        if _ua.find(s) > -1:
            device = 'mobile'
            break
    else:
        device = 'pc'

    if os.path.isfile(tmplpath):
        newval = dict(values)
        newval['path'] = handler.request.path
        newval['device'] = device

        o = template.render(tmplpath, newval)
        handler.response.out.write(o)
        return True
    else:
        return False

def _oauth_handler():
    _con_key = 'xxxxxxxxxxxxxxxxxxxxxx'
    _con_sec = 'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'

    return tweepy.OAuthHandler(consumer_key = _con_key,
                               consumer_secret = _con_sec)

##
class HomeHandler(webapp.RequestHandler):
    def get(self):
        user_info = _login_user(self)
        if not user_info:
            return self.redirect('/')

        _render(self, 'home.html', {'user_info': user_info,
                                    'delays': DELAYS})


class AuthHandler(webapp.RequestHandler):
    def get(self, mode = ''):
        if mode == 'login':
            auth = _oauth_handler()
            auth_url = auth.get_authorization_url()
            memcache.set(auth.request_token.key,
                         auth.request_token.secret,
                         3600)
            return self.redirect(auth_url)

        elif mode == 'verify':
            auth = _oauth_handler()
            ver = self.request.get('oauth_verifier')
            req_key = self.request.get('oauth_token')
            req_sec = memcache.get(req_key)
            auth.set_request_token(req_key, req_sec)
            acc_token = auth.get_access_token(ver)

            api = tweepy.API(auth_handler = auth)
            me = api.me()

            if not UserInfo.all().filter('twitter_id =', str(me.id)).get():
                user_info = UserInfo(twitter_id = str(me.id),
                                     screen_name = me.screen_name,
                                     name = me.name,
                                     image = me.profile_image_url,
                                     acc_key = acc_token.key,
                                     acc_sec = acc_token.secret)
                user_info.put()

            self.session = Session()
            self.session.delete_item('twitter_id')
            self.session['twitter_id'] = str(me.id)

            return self.redirect('/home')

        elif mode == 'logout':
            user_info = _login_user(self)
            if user_info:
                self.session = Session()
                self.session.delete_item('twitter_id')

            return self.redirect('/')
            

class TopHandler(webapp.RequestHandler):
    def get(self):
        user_info = _login_user(self)

        if user_info:
            return self.redirect('/home')
        else:
            _render(self, 'toppage.html')


class UpdateHandler(webapp.RequestHandler):
    def post(self):
        user_info = _login_user(self)
        if not user_info:
            return self.redirect('/')

        message = self.request.get('message').strip()
        delay = self.request.get('delay').strip()
        
        if len(message) == 0:
            error = '文字が入力されていません。'
        elif len(message) > 119:
            error = '入力文字数が多過ぎます。'
        else:
            error = ''

        if delay.isdigit() and int(delay) in DELAYS:
            delay = int(delay)
        else:
            delay = 1

        ps = u' なお、このつぶやきは%d分後に消滅する。' % delay

        if error:
            _render(self, 'home.html',
                    {'user_info': user_info, 'delays': DELAYS, 'error': error})
        else:
            auth = _oauth_handler()
            auth.set_access_token(user_info.acc_key, user_info.acc_sec)
            api = tweepy.API(auth_handler = auth)
            tweet = api.update_status(message + ps)

            taskqueue.add(url = '/remove',
                          params = {'acc_key': user_info.acc_key,
                                    'acc_sec': user_info.acc_sec,
                                    'tweet_id': tweet.id},
                          countdown = delay * 60)

            return self.redirect('/home')


class RemoveHandler(webapp.RequestHandler):
    def post(self):
        acc_key = self.request.get('acc_key').strip()
        acc_sec = self.request.get('acc_sec').strip()
        tweet_id = int(self.request.get('tweet_id').strip())

        if int(self.request.headers.environ['HTTP_X_APPENGINE_TASKRETRYCOUNT']) > 3:
            logging.error('Retried 3 times to destroy "%d"' % tweet_id)
            return

        auth = _oauth_handler()
        auth.set_access_token(acc_key, acc_sec)
        api = tweepy.API(auth_handler = auth)
        api.destroy_status(id = tweet_id)
