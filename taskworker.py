#-*- coding: utf-8 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from handlers import RemoveHandler

##
application = webapp.WSGIApplication(
    [('/remove', RemoveHandler),],
    debug = True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
