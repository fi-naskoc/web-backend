# -*- coding: utf-8 -*-

bind='127.0.0.1:3030'
pidfile='gunicorn_pid'
daemon=True
errorlog='gunicorn_error.log'
workers=4
timeout=60

def pre_request(worker, req):
	if req.path.startswith('/content/'):
		req.query = 'path=' + req.path[9:]
		req.path = '/content'
	if req.path.startswith('/taskContent/'):
		parts = req.path.split("/")
		req.query = 'path=' + '/'.join(parts[4:])
		req.path = '/task-content/' + parts[2] + '/' + parts[3]

