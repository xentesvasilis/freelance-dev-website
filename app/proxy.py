"""Opt-in adapter for Railway's edge-only HTTP ingress.

Enable only when all callers reaching the WSGI socket are trusted proxies/peers.
Header names are not authentication. Never expose the socket via a TCP proxy.
"""
from ipaddress import ip_address

from werkzeug.middleware.proxy_fix import ProxyFix


class RailwayProxy:
    def __init__(self, app):
        # Railway documents X-Real-IP, not an X-Forwarded-For hop count.
        # Preserve Host for Flask TRUSTED_HOSTS; ignore forwarded host/port/prefix.
        self.app = ProxyFix(app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)

    def __call__(self, environ, start_response):
        address = environ.get("HTTP_X_REAL_IP", "")
        try:
            environ["REMOTE_ADDR"] = str(ip_address(address))
        except ValueError:
            pass  # Missing/malformed edge IP retains the socket peer address.
        return self.app(environ, start_response)
