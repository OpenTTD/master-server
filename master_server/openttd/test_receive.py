import pytest

from .receive import OpenTTDProtocolReceive
from .protocol.enums import (
    PacketUDPType,
    SLTType,
)
from .protocol.exceptions import (
    PacketInvalidData,
    PacketInvalidSize,
    PacketInvalidType,
)
from .protocol.source import Source


@pytest.mark.parametrize(
    "data, result",
    [
        (b"\x04\x00\x06\x01", (PacketUDPType.PACKET_UDP_CLIENT_GET_LIST, {"slt": SLTType.SLT_IPv4})),
    ],
)
def test_receive_packet_success(data, result):
    assert OpenTTDProtocolReceive().receive_packet(None, data) == result


@pytest.mark.parametrize(
    "data, exception",
    [
        (b"\x05\x00\x06\x01", PacketInvalidSize),
        (b"\x03\x00\x06\x01", PacketInvalidSize),
        (b"\x03\x00\xFF", PacketInvalidType),
        (b"\x03\x00\x00", PacketInvalidType),
    ],
)
def test_receive_packet_failure(data, exception):
    with pytest.raises(exception):
        OpenTTDProtocolReceive().receive_packet(None, data)


@pytest.mark.parametrize(
    "ip, data, result",
    [
        # Version 1
        (None, b"\x01", {"slt": SLTType.SLT_IPv4}),
        # Version 2, IPv4
        (None, b"\x02\x00", {"slt": SLTType.SLT_IPv4}),
        # Version 2, IPv6
        (None, b"\x02\x01", {"slt": SLTType.SLT_IPv6}),
        # Version 2, Autodetect
        ("127.0.0.1", b"\x02\x02", {"slt": SLTType.SLT_IPv4}),
        ("::1", b"\x02\x02", {"slt": SLTType.SLT_IPv6}),
        ("::ffff:127.0.0.1", b"\x02\x02", {"slt": SLTType.SLT_IPv4}),
    ],
)
def test_receive_PACKET_UDP_CLIENT_GET_LIST_success(ip, data, result):
    if ip is None:
        source = None
    else:
        source = Source(None, None, ip, None)

    assert OpenTTDProtocolReceive.receive_PACKET_UDP_CLIENT_GET_LIST(source, data) == result


@pytest.mark.parametrize(
    "data",
    [
        # Too few data
        b"",
        b"\x02",
        # Too much data
        b"\x01\xFF",
        b"\x02\x00\xFF",
        # Invalid version number
        b"\x00",
        b"\x03",
        # Invalid STL
        b"\x02\x03",
    ],
)
def test_receive_PACKET_UDP_CLIENT_GET_LIST_failure(data):
    with pytest.raises(PacketInvalidData):
        assert OpenTTDProtocolReceive.receive_PACKET_UDP_CLIENT_GET_LIST(None, data)


@pytest.mark.parametrize(
    "data, result",
    [
        # Version 1
        (b"OpenTTDRegister\x00\x01\x34\x12", {"port": 0x1234, "session_key": None}),
        # Version 2
        (b"OpenTTDRegister\x00\x02\x34\x12\x01\x00\x00\x00\x00\x00\x00\x00", {"port": 0x1234, "session_key": 1}),
    ],
)
def test_receive_PACKET_UDP_SERVER_REGISTER_success(data, result):
    assert OpenTTDProtocolReceive.receive_PACKET_UDP_SERVER_REGISTER(None, data) == result


@pytest.mark.parametrize(
    "data",
    [
        # Too few data
        b"",
        b"OpenTTDRegister\x00\x01\x34",
        b"OpenTTDRegister\x00\x02\x34\x12\x01\x00\x00\x00\x00\x00\x00",
        # Too much data
        b"OpenTTDRegister\x00\x01\x34\x12\xFF",
        b"OpenTTDRegister\x00\x02\x34\x12\x01\x00\x00\x00\x00\x00\x00\x00\xFF",
        # Invalid version number
        b"OpenTTDRegister\x00\x00\x34\x12",
        b"OpenTTDRegister\x00\x03\x34\x12",
        # Wrong welcome message
        b"OpenTTDNotRegister\x00\x01\x34\x12",
    ],
)
def test_receive_PACKET_UDP_SERVER_REGISTER_failure(data):
    with pytest.raises(PacketInvalidData):
        assert OpenTTDProtocolReceive.receive_PACKET_UDP_SERVER_REGISTER(None, data)


@pytest.mark.parametrize(
    "data, result",
    [
        # Version 1
        (b"\x01\x34\x12", {"port": 0x1234}),
        # Version 2
        (b"\x02\x34\x12", {"port": 0x1234}),
    ],
)
def test_receive_PACKET_UDP_SERVER_UNREGISTER_success(data, result):
    assert OpenTTDProtocolReceive.receive_PACKET_UDP_SERVER_UNREGISTER(None, data) == result


@pytest.mark.parametrize(
    "data",
    [
        # Too few data
        b"",
        b"\x01\x34",
        b"\x02\x34",
        # Too much data
        b"\x01\x34\x12\xFF",
        b"\x02\x34\x12\xFF",
        # Invalid version number
        b"\x00\x34\x12",
        b"\x03\x34\x12",
    ],
)
def test_receive_PACKET_UDP_SERVER_UNREGISTER_failure(data):
    with pytest.raises(PacketInvalidData):
        assert OpenTTDProtocolReceive.receive_PACKET_UDP_SERVER_UNREGISTER(None, data)
