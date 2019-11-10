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

        self._session_counter = random.randrange(0, 256 * 256)

    def _get_next_session_key(self):
        #           |63      56       48       40       32       24       16       8       0|
        #           |--------|--------|--------|--------|--------|--------|--------|--------|
        # Version 1 |     unused      |      port       |                ip                 |
        # Version 2 | unused |               time                |     counter     | token  |

        # Add some random values to the counter, making it hard to guess the
        # next value. This avoids collisions if multiple servers register at
        # the same time.
        self._session_counter += random.randrange(1, 16)
        self._session_counter &= 0xFFFF

        # The session key includes a token, to avoid people guessing the
        # session_key of others.
        token = random.randrange(0, 256)

        # Session-key is the current server time combined with the counter
        # and token.
        session_key = (int(time.time()) << 24) | (self._session_counter << 8)

        self.database.store_session_key_token(session_key, token)
        return session_key, token

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
            session_key, token = self._get_next_session_key()
            source.protocol.send_PACKET_UDP_MASTER_SESSION_KEY(source.addr, session_key | token)

            # We don't query the server for now; we first let the server
            # accept the new session-key, and register itself with the new
            # session-key again. The server will notice his registration is
            # not acknowledged, and after a few seconds retries (thinking it
            # got lost because of some UDP packet loss or what-ever).
            return
        else:
            token = session_key & 0xFF
            session_key = (session_key >> 8) << 8

            if not self.database.check_session_key_token(session_key, token):
                log.info("Invalid session-key token from %s:%d; transmitting new session-key", source.ip, source.port)

                # TODO -- If an IP has this wrong for more than 3 times, it is
                # time to put that IP on a ban-list for a bit of time.

                # Send the server a new session-key, as clearly he got a bit
                # confused.
                session_key, token = self._get_next_session_key()
                source.protocol.send_PACKET_UDP_MASTER_SESSION_KEY(source.addr, session_key | token)
                return

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
