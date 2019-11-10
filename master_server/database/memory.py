import logging
import time

from .interface import DatabaseInterface

log = logging.getLogger(__name__)


class Server:
    def __init__(self):
        self.ip_port = set()
        self.last_announcement = None


class Database(DatabaseInterface):
    def __init__(self):
        self._servers = {}
        self._session_key_map = {}
        self._tokens = {}

    def check_session_key_token(self, session_key, token):
        return self._tokens.get(session_key, None) is token

    def store_session_key_token(self, session_key, token):
        self._tokens[session_key] = token

    def _find_session_key(self, server_ip, server_port):
        return self._session_key_map.get((server_ip, server_port), None)

    def server_online(self, session_key, server_ip, server_port):
        existing_session_key = self._find_session_key(server_ip, server_port)

        # This should basically never happen; so resolving this conflict is
        # difficult. The current assumption is that the server registered as
        # two servers (with 2 different session-keys), and should in fact be
        # a single server. So we remove the old entry, and collapse the two
        # registrations on the same session-key.
        if existing_session_key == session_key:
            log.error("Existing registration for %s:%d under different session-key", server_ip, server_port)
            del self._servers[existing_session_key]

        if session_key in self._servers:
            server = self._servers[session_key]
        else:
            server = Server()
            self._servers[session_key] = server
            self._session_key_map[(server_ip, server_port)] = session_key

        server.ip_port.add((server_ip, server_port))
        server.last_announcement = time.time()

        print(f"Server {hex(session_key)} with {server_ip}:{server_port} online")

    def server_offline(self, server_ip, server_port):
        session_key = self._find_session_key(server_ip, server_port)
        # When unregistering with multiple IPs, it also sends the unregister
        # for every IP. So there is a good chance we already no longer know
        # about this server.
        if session_key is None:
            return

        print(f"Server {hex(session_key)} offline")

        del self._servers[session_key]
