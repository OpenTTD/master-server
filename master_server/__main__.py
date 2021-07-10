import click
import logging

from openttd_helpers import click_helper
from openttd_helpers.logging_helper import click_logging
from openttd_helpers.sentry_helper import click_sentry

from .database.dynamodb import click_database_dynamodb
from .database.redis import click_database_redis
from .openttd.udp import click_proxy_protocol

log = logging.getLogger(__name__)


@click_helper.command()
@click_logging  # Should always be on top, as it initializes the logging
@click_sentry
@click.option(
    "--bind", help="The IP to bind the server to", multiple=True, default=["::1", "127.0.0.1"], show_default=True
)
@click.option("--msu-port", help="Port of the MSU server", default=3978, show_default=True, metavar="PORT")
@click.option("--web-port", help="Port of the web server.", default=80, show_default=True, metavar="PORT")
@click.option(
    "--app",
    type=click.Choice(["master_server", "web_api"], case_sensitive=False),
    required=True,
    callback=click_helper.import_module("master_server.application", "Application"),
)
@click.option(
    "--db",
    type=click.Choice(["dynamodb", "redis"], case_sensitive=False),
    required=True,
    callback=click_helper.import_module("master_server.database", "Database"),
)
@click_database_dynamodb
@click_database_redis
@click_proxy_protocol
def main(bind, msu_port, web_port, app, db):
    database = db()
    application = app(database)
    application.run(bind, msu_port, web_port)


if __name__ == "__main__":
    main(auto_envvar_prefix="MASTER_SERVER")
