from .protocol.enums import PacketUDPType
from .protocol.write import (
    write_init,
    write_uint8,
    write_uint16,
    write_uint64,
    write_presend,
)


class OpenTTDProtocolSend:
    def send_PACKET_UDP_MASTER_SESSION_KEY(self, addr, session_key, new_connection=False):
        data = write_init(PacketUDPType.PACKET_UDP_MASTER_SESSION_KEY)
        data = write_uint64(data, session_key)
        data = write_presend(data)
        return self.send_packet(addr, data, new_connection=new_connection)

    def send_PACKET_UDP_MASTER_ACK_REGISTER(self, addr, new_connection=False):
        data = write_init(PacketUDPType.PACKET_UDP_MASTER_ACK_REGISTER)
        data = write_presend(data)
        return self.send_packet(addr, data, new_connection=new_connection)

    def send_PACKET_UDP_CLIENT_FIND_SERVER(self, addr, new_connection=False):
        data = write_init(PacketUDPType.PACKET_UDP_CLIENT_FIND_SERVER)
        data = write_presend(data)
        return self.send_packet(addr, data, new_connection=new_connection)

    def send_PACKET_UDP_MASTER_RESPONSE_LIST(self, addr, slt, servers, new_connection=False):
        data = write_init(PacketUDPType.PACKET_UDP_MASTER_RESPONSE_LIST)
        data = write_uint8(data, slt.value + 1)
        data = write_uint16(data, len(servers))
        for server in servers:
            packed = server["ip"].packed
            for i in range(len(packed)):
                data = write_uint8(data, packed[i])
            data = write_uint16(data, server["port"])
        data = write_presend(data)
        return self.send_packet(addr, data, new_connection=new_connection)
