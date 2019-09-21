import logging
import random
import time

from .common import Common

log = logging.getLogger(__name__)


class Application(Common):
    def __init__(self, database):
        super().__init__()

        self.database = database
        self.protocol = None

        self._init_session_key()
        # There can be running multiple servers at once, all connected to a
        # single database. To prevent them issuing the same session_key, check
        # for this rare corner case.
        while not self.database.check_initial_session_key(self._current_session_key):
            self._init_session_key()

    def _init_session_key(self):
        # Version 1 uses 32+16 bits (IPv4 + port) for session-keys.
        # To avoid conflicts between session-keys generated for version 1 and
        # version 2, the first session-key we generate for version 2 should be
        # passed the version 1 format.
        # We use time() to initialize the first key; time() currently is already
        # past 2^31 seconds, so bitshifting it with 17 would mean it also uses
        # 48 bits like version 1. Adding another bitshift of 3 should give
        # sufficient space to differentiate between version 1 and version 2.
        # In other words: if the value is greater than 2^51, it is a version 2
        # session-key; otherwise it is a version 1. This means they will never
        # collide.
        self._current_session_key = int(time.time()) << 20

    def _get_next_session_key(self):
        # Jump forward with some (semi) unpredictable amount
        self._current_session_key += 1 + random.randrange(0, 255)
        return self._current_session_key

    def receive_PACKET_UDP_SERVER_REGISTER(self, source, port, session_key):
        # session_key of None means it was version 1.
        if session_key is None:
            # To be able to use session-keys as an unique ID, also
            # generate a session-key for version 1, but based on
            # static information of the server.
            session_key = int(source.ip) | (port << 32)
        elif session_key == 0:
            # Session-keys were introduced in version 2.
            # This session-key tracks the same server over multiple IPs.
            # On first contact with the Master Server, a session-key is send
            # back to the server. This session-key is reused for any further
            # announcement, also on other IPs.
            session_key = self._get_next_session_key()
            source.protocol.send_PACKET_UDP_MASTER_SESSION_KEY(source.addr, session_key)

        # We use the ip as announced by the socket, and the port as given
        # in the packet. This is where the server should be located at.
        #
        # Save the original addr for after we queried the server (user_data);
        # once we know the server is reachable, we will inform the server over
        # this addr that it is registered.
        # The flow is like this:
        # - random UDP port (source.addr) asks us to register a given server
        #   port.
        # - we query that server port (server_addr).
        # - if we get answer (via server_addr), we tell over that random UDP
        #   port (source.addr) the registration is done.
        # ('random UDP port' in this context means one that is auto-assigned
        #  by the TCP/IP stack on the server side; it is not sent via the
        #  server UDP port).
        self.query_server(source.ip, port, source.protocol, user_data=(session_key, source.addr))

    def receive_PACKET_UDP_SERVER_RESPONSE(self, source, **info):
        response = self.query_server_response(source.ip, source.port)
        if response is None:
            return
        session_key, register_addr = response

        # This server can now be marked as online.
        self.database.server_online(session_key, source.ip, source.port)

        # Inform the server that he is now registered.
        source.protocol.send_PACKET_UDP_MASTER_ACK_REGISTER(register_addr)

    def receive_PACKET_UDP_SERVER_UNREGISTER(self, source, port):
        self.database.server_offline(source.ip, port)

    def receive_PACKET_UDP_CLIENT_GET_LIST(self, source, slt):
        print(source, slt)
        # TODO -- Implement this
