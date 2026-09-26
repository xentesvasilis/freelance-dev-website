"""Small Railway staging service; automatically loaded by Gunicorn."""
import os

bind = "0.0.0.0:" + str(int(os.environ.get("PORT", "8000")))
workers = 1
worker_class = "gthread"
threads = 2
timeout = 60
graceful_timeout = 30
keepalive = 5
preload_app = False
# The explicit application proxy adapter owns scheme/IP handling.
forwarded_allow_ips = ""
secure_scheme_headers = {}
accesslog = "-"
errorlog = "-"
loglevel = "info"
# Omit IPs, URLs, query strings, headers and submitted content.
access_log_format = "%(m)s %(s)s %(B)s %(L)s"
