import abc


class DatabaseInterface(abc.ABC):
    @abc.abstractmethod
    def check_session_key_token(self, session_key, token):
        """Check if this session key token exists and is valid."""

    @abc.abstractmethod
    def store_session_key_token(self, session_key, token):
        """Store a new session key token."""

    @abc.abstractmethod
    def server_online(self, session_key, server_ip, server_port):
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
