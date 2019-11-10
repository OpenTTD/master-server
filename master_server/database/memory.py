import time

from .interface import DatabaseInterface


class Server:
    def __init__(self):
        self.ip_port = set()
        self.last_announcement = None


class Database(DatabaseInterface):
    def __init__(self):
        self._session_keys = set()
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
        if session_key in self._servers:
            server = self._servers[session_key]
        else:
            existing_session_key = self._find_session_key(server_ip, server_port)
            if existing_session_key:
                print(f"Server on {server_ip}:{server_port} already had a registration")
                # TODO -- What is the conflict resolvement here?
                # We can either overwrite the known server, and update it with
                # the session_key, or we can remove the known server, and
                # create a new entry.

            server = Server()
            self._servers[session_key] = server
            self._session_key_map[(server_ip, server_port)] = session_key

        server.ip_port.add((server_ip, server_port))
        server.last_announcement = time.time()

        print(f"Server {session_key} with {server_ip}:{server_port} online")

    def server_offline(self, server_ip, server_port):
        session_key = self._find_session_key(server_ip, server_port)

        print(f"Server {session_key} offline")

        del self._servers[session_key]
