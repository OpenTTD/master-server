import struct

from .exceptions import PacketTooBig

# Empirical evidence has shown this value to work best. OpenTTD uses 1460 MTU,
# but time has shown that not all our clients can receive a packet of that
# size over UDP (as there is no fragmenting on UDP). Lowering this value by
# 100 seems sufficient to allow clients with GREs, VPNs, etc to query the
# master-server successfully.
SAFE_MTU = 1360


def write_init(type):
    return b"\x00\x00" + struct.pack("<B", type)


def write_uint8(data, value):
    return data + struct.pack("<B", value)


def write_uint16(data, value):
    return data + struct.pack("<H", value)


def write_uint32(data, value):
    return data + struct.pack("<I", value)


def write_uint64(data, value):
    return data + struct.pack("<Q", value)


def write_string(data, value):
    return data + value.encode() + b"\x00"


def write_presend(data):
    if len(data) > SAFE_MTU:
        raise PacketTooBig(len(data))
    return struct.pack("<H", len(data)) + data[2:]
