import ipaddress

from .protocol.enums import (
    PacketUDPType,
    SLTType,
)
from .protocol.exceptions import (
    PacketInvalidData,
    PacketInvalidSize,
    PacketInvalidType,
)
from .protocol.read import (
    read_bytes,
    read_string,
    read_uint8,
    read_uint16,
    read_uint32,
    read_uint64,
)

NETWORK_MASTER_SERVER_WELCOME_MESSAGE = "OpenTTDRegister"

# The minimum starting year on the original TTD.
ORIGINAL_BASE_YEAR = 1920
# In GameInfo version 3 the date was changed to be counted from the year zero.
# This offset is added to version 2 and 1 to have the date the same for all
# versions. It is the amount of days from year 0 to 1920.
DAYS_TILL_ORIGINAL_BASE_YEAR = (
    365 * ORIGINAL_BASE_YEAR + ORIGINAL_BASE_YEAR // 4 - ORIGINAL_BASE_YEAR // 100 + ORIGINAL_BASE_YEAR // 400
)


class OpenTTDProtocolReceive:
    def receive_packet(self, source, data):
        # Check length of packet
        length, data = read_uint16(data)
        if length != len(data) + 2:
            raise PacketInvalidSize(len(data) + 2, length)

        # Check if type is in range
        type, data = read_uint8(data)
        if type >= PacketUDPType.PACKET_UDP_END:
            raise PacketInvalidType(type)

        # Check if we expect this packet
        type = PacketUDPType(type)
        func = getattr(self, f"receive_{type.name}", None)
        if func is None:
            raise PacketInvalidType(type)

        # Process this packet
        kwargs = func(source, data)
        return type, kwargs

    @staticmethod
    def receive_PACKET_UDP_CLIENT_GET_LIST(source, data):
        version, data = read_uint8(data)

        if version == 2:
            slt, data = read_uint8(data)
        else:
            slt = SLTType.SLT_IPv4.value

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected")

        if version < 1 or version > 2:
            raise PacketInvalidData("wrong version", version)

        if slt >= SLTType.SLT_END:
            raise PacketInvalidData("invalid SLT", slt)

        slt = SLTType(slt)
        if slt == SLTType.SLT_AUTODETECT:
            if isinstance(source.ip, ipaddress.IPv6Address):
                slt = SLTType.SLT_IPv6
            else:
                slt = SLTType.SLT_IPv4

        return {"slt": slt}

    @staticmethod
    def receive_PACKET_UDP_SERVER_REGISTER(source, data):
        welcome, data = read_string(data)
        version, data = read_uint8(data)
        port, data = read_uint16(data)
        session_key = None

        if version == 2:
            session_key, data = read_uint64(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected")

        if welcome != NETWORK_MASTER_SERVER_WELCOME_MESSAGE:
            raise PacketInvalidData("wrong welcome message", welcome)
        if version < 1 or version > 2:
            raise PacketInvalidData("wrong version", version)

        return {"port": port, "session_key": session_key}

    @staticmethod
    def receive_PACKET_UDP_SERVER_RESPONSE(source, data):
        payload = {
            name: None
            for name in [
                "num_grfs",
                "grfs",
                "game_date",
                "start_date",
                "companies_max",
                "companies_on",
                "spectators_max",
                "server_name",
                "server_revision",
                "server_lang",
                "use_password",
                "clients_max",
                "clients_on",
                "spectators_on",
                "map_name",
                "map_width",
                "map_height",
                "map_set",
                "dedicated",
            ]
        }

        game_info_version, data = read_uint8(data)

        if game_info_version >= 4:
            payload["num_grfs"], data = read_uint8(data)
            payload["grfs"] = []
            for _ in range(payload["num_grfs"]):
                grfid, data = read_uint32(data)
                md5sum, data = read_bytes(data, 16)
                payload["grfs"].append({"grfid": grfid, "md5sum": md5sum})

        if game_info_version >= 3:
            payload["game_date"], data = read_uint32(data)
            payload["start_date"], data = read_uint32(data)

        if game_info_version >= 2:
            payload["companies_max"], data = read_uint8(data)
            payload["companies_on"], data = read_uint8(data)
            payload["spectators_max"], data = read_uint8(data)

        if game_info_version >= 1:
            payload["server_name"], data = read_string(data)
            payload["server_revision"], data = read_string(data)
            payload["server_lang"], data = read_uint8(data)
            payload["use_password"], data = read_uint8(data)
            payload["clients_max"], data = read_uint8(data)
            payload["clients_on"], data = read_uint8(data)
            payload["spectators_on"], data = read_uint8(data)
            if game_info_version < 3:
                payload["game_date"], data = read_uint16(data)
                payload["game_date"] += DAYS_TILL_ORIGINAL_BASE_YEAR
                payload["start_date"], data = read_uint16(data)
                payload["start_date"] += DAYS_TILL_ORIGINAL_BASE_YEAR
            payload["map_name"], data = read_string(data)
            payload["map_width"], data = read_uint16(data)
            payload["map_height"], data = read_uint16(data)
            payload["map_set"], data = read_uint8(data)
            payload["dedicated"], data = read_uint8(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected")

        return payload

    @staticmethod
    def receive_PACKET_UDP_SERVER_UNREGISTER(source, data):
        version, data = read_uint8(data)
        port, data = read_uint16(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected")

        if version < 1 or version > 2:
            raise PacketInvalidData("wrong version", version)

        return {"port": port}
