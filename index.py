#-*- coding: utf-8 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from handlers import HomeHandler, AuthHandler, UpdateHandler, TopHandler

##
application = webapp.WSGIApplication(
    [('/home', HomeHandler),
     ('/auth/(.*)', AuthHandler),
     ('/update', UpdateHandler),
     ('/.*', TopHandler),],
    debug = True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
