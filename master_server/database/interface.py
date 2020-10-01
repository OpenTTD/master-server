import abc


class DatabaseInterface(abc.ABC):
    @abc.abstractmethod
    def check_session_key_token(self, session_key, token):
        """Check if this session key token exists and is valid."""

    @abc.abstractmethod
    def store_session_key_token(self, session_key, token):
        """Store a new session key token."""

    @abc.abstractmethod
    def server_online(self, session_key, server_ip, server_port, info):
        """
        Mark the specified server online.

        The session_key is the unique identifier here. There can be several
        ip/port combinations to a single session_key. They are all the same
        server.

        If the server is not known yet, create the server entry.
        """

    @abc.abstractmethod
    def server_offline(self, server_ip, server_port):
        """Mark the specified server offline."""

    @abc.abstractmethod
    def get_server_list_for_client(self, ipv6_list):
        """
        Get the server-list for clients.

        This list contains only IP/port pairs, and no additional information.
        """

    @abc.abstractmethod
    def get_server_info_for_web(self, server_id):
        """Get details about a single server."""

    @abc.abstractmethod
    def get_server_list_for_web(self):
        """
        Get the server-list for web.

        This list contains all the detailed information for each server.
        """
