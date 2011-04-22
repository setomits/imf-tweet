#-*- coding: utf-8 -*-

from google.appengine.ext import db

class UserInfo(db.Model):
    twitter_id = db.StringProperty(required = True)
    screen_name = db.StringProperty(required = True)
    name = db.StringProperty(required = True)
    image = db.LinkProperty(required = True)
    acc_key = db.StringProperty(required =True)
    acc_sec = db.StringProperty(required =True)
