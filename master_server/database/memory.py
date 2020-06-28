import logging
import time

from .interface import DatabaseInterface

log = logging.getLogger(__name__)


class Server:
    def __init__(self):
        self.ip_port = set()
        self.last_announcement = None
        self.info = None


class Database(DatabaseInterface):
    def __init__(self):
        self._servers = {}
        self._session_key_map = {}
        self._tokens = {}

    def check_session_key_token(self, session_key, token):
        if session_key not in self._tokens:
            # We don't know the session_key; so the only thing we can do is
            # take it on face-value that the token is valid.
            self.store_session_key_token(session_key, token)
            return True

        return self._tokens[session_key] == token

    def store_session_key_token(self, session_key, token):
        self._tokens[session_key] = token

    def _find_session_key(self, server_ip, server_port):
        return self._session_key_map.get((server_ip, server_port), None)

    def _forget_server_ip_port(self, server_ip, server_port):
        session_key = self._session_key_map[(server_ip, server_port)]
        del self._session_key_map[(server_ip, server_port)]

        server = self._servers[session_key]
        server.ip_port.remove((server_ip, server_port))
        if not server.ip_port:
            print(f"Server {hex(session_key)} offline")
            del self._servers[session_key]

    def server_online(self, session_key, server_ip, server_port, info):
        # If a server-ip:server-port is already known, but under another
        # session-key, it most likely means the server has not deregistered
        # itself (due to a crash for example), didn't remember his session-key
        # and is reannouncing itself. In this case, simply forget about the
        # old session-key, and continue on with the new.
        existing_session_key = self._find_session_key(server_ip, server_port)
        if existing_session_key and existing_session_key != session_key:
            self._forget_server_ip_port(server_ip, server_port)

        server = self._servers.get(session_key, None)
        if not server:
            server = Server()
            self._servers[session_key] = server

        self._session_key_map[(server_ip, server_port)] = session_key
        server.ip_port.add((server_ip, server_port))
        server.last_announcement = time.time()
        server.info = info

        print(f"Server {hex(session_key)} with {server_ip}:{server_port} online ({info['clients_on']} players)")

    def server_offline(self, server_ip, server_port):
        session_key = self._find_session_key(server_ip, server_port)
        if session_key is None:
            log.error("Server %s:%d, that was not registered, went offline", server_ip, server_port)
            return

        self._forget_server_ip_port(server_ip, server_port)
