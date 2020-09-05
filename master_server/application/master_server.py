import asyncio
import logging
import random
import time

from .master_server_query import Common
from ..openttd.protocol.enums import SLTType
from ..openttd.protocol.write import SAFE_MTU

log = logging.getLogger(__name__)

# (SAFE_MTU - PacketSize - PacketType - type - count) / (in[6]_addr + port)
MAX_COUNT = {
    SLTType.SLT_IPv4: (SAFE_MTU - 2 - 1 - 2 - 1) // (4 + 2),
    SLTType.SLT_IPv6: (SAFE_MTU - 2 - 1 - 2 - 1) // (16 + 2),
}
# Cache the in-game serverlist for 30 seconds.
SERVERS_CACHE_EXPIRE = 30
# How many seconds between stale-checks.
TIME_BETWEEN_STALE_CHECK = 60 * 5


class Application(Common):
    def __init__(self, database):
        super().__init__()

        self.database = database
        self.protocol = None

        self._session_counter = random.randrange(0, 256 * 256)
        self._servers_cache = {
            SLTType.SLT_IPv4: None,
            SLTType.SLT_IPv6: None,
        }

        asyncio.ensure_future(self.check_stale_servers())

    async def check_stale_servers(self):
        while True:
            await asyncio.sleep(TIME_BETWEEN_STALE_CHECK)
            self.database.check_stale_servers()

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
        if not self.database.server_online(session_key, source.ip, source.port, info):
            return

        # Inform the server that he is now registered.
        source.protocol.send_PACKET_UDP_MASTER_ACK_REGISTER(register_addr)

    def receive_PACKET_UDP_SERVER_UNREGISTER(self, source, port):
        self.database.server_offline(source.ip, port)

    def receive_PACKET_UDP_CLIENT_GET_LIST(self, source, slt):
        # Fetching all the servers is pretty expensive, so rate limit how often we do this.
        if self._servers_cache[slt] is None or time.time() > self._servers_cache[slt]["expire"]:
            servers = self.database.get_server_list_for_client(slt == SLTType.SLT_IPv6)

            self._servers_cache[slt] = {
                "servers": servers,
                "expire": time.time() + SERVERS_CACHE_EXPIRE,
            }

        # Send the servers in packets that fit within the SAFE_MTU.
        servers = self._servers_cache[slt]["servers"]
        for i in range(0, len(servers), MAX_COUNT[slt]):
            server_slice = servers[i : i + MAX_COUNT[slt]]
            source.protocol.send_PACKET_UDP_MASTER_RESPONSE_LIST(source.addr, slt, server_slice)
