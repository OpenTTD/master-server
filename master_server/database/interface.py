import abc


class DatabaseInterface(abc.ABC):
    @abc.abstractmethod
    def check_initial_session_key(self, session_key):
        """
        Check if there is any other server running with this session-key.

        If not, this session_key should be recorded as "in use".
        """

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
