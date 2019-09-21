import asyncio
import logging

from .protocol.exceptions import PacketInvalid
from .protocol.source import Source
from .receive import OpenTTDProtocolReceive
from .send import OpenTTDProtocolSend

log = logging.getLogger(__name__)


class OpenTTDProtocolUDP(asyncio.DatagramProtocol, OpenTTDProtocolReceive, OpenTTDProtocolSend):
    def __init__(self, callback_class):
        super().__init__()
        self._callback = callback_class
        self._callback.protocol = self
        self.is_ipv6 = None

    def connection_made(self, transport):
        self.transport = transport
        if len(transport.get_extra_info("sockname")) == 4:
            self.is_ipv6 = True
        else:
            self.is_ipv6 = False

    def _detect_source_ip_port(self, socket_addr, data):
        if data[0:5] == b"PROXY":
            # This message arrived via the proxy protocol; use the information
            # from this to figure out the real ip and port.
            proxy_end = data.find(b"\r\n")
            proxy = data[0:proxy_end].decode()
            data = data[proxy_end + 2 :]

            # Example how 'proxy' looks:
            #  PROXY TCP4 127.0.0.1 127.0.0.1 33487 12345

            (_, _, ip, _, port, _) = proxy.split(" ")
            source = Source(self, socket_addr, ip, int(port))
        else:
            source = Source(self, socket_addr, socket_addr[0], socket_addr[1])

        return source, data

    def datagram_received(self, data, socket_addr):
        try:
            source, data = self._detect_source_ip_port(socket_addr, data)
        except Exception as err:
            log.exception("Error detecting PROXY protocol %r: %r", socket_addr, err)
            return

        try:
            type, kwargs = self.receive_packet(source, data)
        except PacketInvalid as err:
            log.info("Dropping invalid packet from %r: %r", socket_addr, err)
            return

        getattr(self._callback, f"receive_{type.name}")(source, **kwargs)

    def error_received(self, exc):
        print("error on socket: ", exc)

    def send_packet(self, socket_addr, data):
        self.transport.sendto(data, socket_addr)
