import click
import logging

from .helpers.click import (
    click_additional_options,
    import_module,
)
from .helpers.sentry import click_sentry
from .openttd.udp import click_proxy_protocol

log = logging.getLogger(__name__)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click_additional_options
def click_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
    )


@click.command(context_settings=CONTEXT_SETTINGS)
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
    callback=import_module("master_server.application", "Application"),
)
@click.option(
    "--db",
    type=click.Choice(["dynamodb"], case_sensitive=False),
    required=True,
    callback=import_module("master_server.database", "Database"),
)
@click.option("--dynamodb-host", help="Hostname to use for the DynamoDB connection", default=None)
@click.option("--dynamodb-region", help="Region to use for the DynamoDB connection", default=None)
@click_proxy_protocol
def main(bind, msu_port, web_port, app, db, dynamodb_host, dynamodb_region):
    database = db(dynamodb_host, dynamodb_region)
    application = app(database)
    application.run(bind, msu_port, web_port)


if __name__ == "__main__":
    main(auto_envvar_prefix="MASTER_SERVER")
