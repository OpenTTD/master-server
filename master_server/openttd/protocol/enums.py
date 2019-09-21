import enum


# Copy from OpenTTD/src/network/core/udp.h
class PacketUDPType(enum.IntEnum):
    PACKET_UDP_CLIENT_FIND_SERVER = 0  # Queries a game server for game information
    PACKET_UDP_SERVER_RESPONSE = 1  # Reply of the game server with game information
    PACKET_UDP_CLIENT_DETAIL_INFO = 2  # Queries a game server about details of the game, such as companies
    PACKET_UDP_SERVER_DETAIL_INFO = 3  # Reply of the game server about details of the game, such as companies
    PACKET_UDP_SERVER_REGISTER = 4  # Packet to register itself to the master server
    PACKET_UDP_MASTER_ACK_REGISTER = 5  # Packet indicating registration has succeeded
    PACKET_UDP_CLIENT_GET_LIST = 6  # Request for serverlist from master server
    PACKET_UDP_MASTER_RESPONSE_LIST = 7  # Response from master server with server ip's + port's
    PACKET_UDP_SERVER_UNREGISTER = 8  # Request to be removed from the server-list
    PACKET_UDP_CLIENT_GET_NEWGRFS = 9  # Requests the name for a list of GRFs (GRF_ID and MD5)
    PACKET_UDP_SERVER_NEWGRFS = 10  # Sends the list of NewGRF's requested.
    PACKET_UDP_MASTER_SESSION_KEY = 11  # Sends a fresh session key to the client
    PACKET_UDP_END = 12  # Must ALWAYS be on the end of this list!! (period)


class SLTType(enum.IntEnum):
    SLT_IPv4 = 0
    SLT_IPv6 = 1
    SLT_AUTODETECT = 2
    SLT_END = 3
