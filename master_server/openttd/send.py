from .protocol.enums import PacketUDPType
from .protocol.write import (
    write_init,
    write_uint64,
    write_presend,
)


class OpenTTDProtocolSend:
    def send_PACKET_UDP_MASTER_SESSION_KEY(self, addr, session_key):
        data = write_init(PacketUDPType.PACKET_UDP_MASTER_SESSION_KEY)
        data = write_uint64(data, session_key)
        data = write_presend(data)
        self.send_packet(addr, data)

    def send_PACKET_UDP_MASTER_ACK_REGISTER(self, addr):
        data = write_init(PacketUDPType.PACKET_UDP_MASTER_ACK_REGISTER)
        data = write_presend(data)
        self.send_packet(addr, data)

    def send_PACKET_UDP_CLIENT_FIND_SERVER(self, addr):
        data = write_init(PacketUDPType.PACKET_UDP_CLIENT_FIND_SERVER)
        data = write_presend(data)
        self.send_packet(addr, data)
