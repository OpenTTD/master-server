import logging

from .common import Common

log = logging.getLogger(__name__)


class Application(Common):
    def __init__(self, database):
        super().__init__(retry_reached_callback=self._retry_reached_callback)

        self.database = database
        self.protocol = None

        # TODO -- Once in a while, query all the servers
        # self.query_server(ip, port, self.protocol)

    def _retry_reached_callback(self, ip, port):
        self.database.server_offline(ip, port)

    def receive_PACKET_UDP_SERVER_RESPONSE(self, source, **info):
        self.query_server_response(source.ip, source.port)

        # TODO -- Update in database
        # TODO -- Request GRF info

        print(source, info)
