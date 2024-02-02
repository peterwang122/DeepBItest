from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from . import settings


class Bi(Flask):
    """A custom Flask app for Bi"""

    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "template_folder": settings.FLASK_TEMPLATE_PATH,
                "static_folder": settings.STATIC_ASSETS_PATH,
                "static_url_path": "/static",
            }
        )
        super(Bi, self).__init__(__name__, *args, **kwargs)
        # Make sure we get the right referral address even behind proxies like nginx.
        self.wsgi_app = ProxyFix(self.wsgi_app, x_for=settings.PROXIES_COUNT, x_host=1)
        # Configure Bi using our settings
        self.config.from_object("bi.settings")


def create_app():
    from . import (
        # authentication,
        handlers,
        limiter,
        mail,
        migrate,
        security,
        tasks,
        feishu
    )
    from .handlers.webpack import configure_webpack
    from .metrics import request as request_metrics
    from .models import db, users
    from .utils import sentry

    sentry.init()
    app = Bi()

    security.init_app(app)
    request_metrics.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    # authentication.init_app(app)
    limiter.init_app(app)
    handlers.init_app(app)
    configure_webpack(app)
    users.init_app(app)
    tasks.init_app(app)
    feishu.init_app(app)

    return app
