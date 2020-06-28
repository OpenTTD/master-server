import asyncio
import click
import logging

from .helpers.click import (
    click_additional_options,
    import_module,
)
from .helpers.sentry import click_sentry
from .openttd import udp
from .openttd.udp import click_proxy_protocol

log = logging.getLogger(__name__)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


async def run_server(application, bind, port):
    loop = asyncio.get_event_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: udp.OpenTTDProtocolUDP(application), local_addr=(bind, port), reuse_port=True
    )
    log.info(f"Listening on {bind}:{port} ...")

    return transport


@click_additional_options
def click_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
    )


@click.command(context_settings=CONTEXT_SETTINGS)
@click_logging  # Should always be on top, as it initializes the logging
@click_sentry
@click.option("--bind", help="The IP to bind the server to", default="::", show_default=True)
@click.option("--port", help="Port of the server", default=3978, show_default=True)
@click.option(
    "--app",
    type=click.Choice(["master_server", "updater"], case_sensitive=False),
    required=True,
    callback=import_module("master_server.application", "Application"),
)
@click.option(
    "--db",
    type=click.Choice(["memory"], case_sensitive=False),
    required=True,
    callback=import_module("master_server.database", "Database"),
)
@click_proxy_protocol
def main(bind, port, app, db):
    database = db()
    application = app(database)

    loop = asyncio.get_event_loop()
    transport = loop.run_until_complete(run_server(application, bind, port))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    log.info(f"Shutting down {app} ...")
    transport.close()


if __name__ == "__main__":
    main(auto_envvar_prefix="MASTER_SERVER")
