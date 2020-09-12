import asyncio
import click
import logging
import pproxy

from .protocol.exceptions import (
    NoProxyProtocol,
    PacketInvalid,
)
from .protocol.source import Source
from .receive import OpenTTDProtocolReceive
from .send import OpenTTDProtocolSend
from ..helpers.click import click_additional_options

log = logging.getLogger(__name__)


class SocksProtocol(asyncio.DatagramProtocol):
    def __init__(self, data, callback):
        self._data = data
        self._callback = callback

    def connection_made(self, transport):
        transport.sendto(self._data)

    def datagram_received(self, data, addr):
        self._callback(data)


class OpenTTDProtocolUDP(asyncio.DatagramProtocol, OpenTTDProtocolReceive, OpenTTDProtocolSend):
    proxy_protocol = False
    socks_proxy = None

    def __init__(self, callback_class):
        super().__init__()
        self._callback = callback_class
        self._callback.protocol = self
        self.is_ipv6 = None
        self._mapping = {}

        if self.socks_proxy:
            self._socks_conn = pproxy.Connection(self.socks_proxy)
            self._socks_addr = (self._socks_conn.host_name, self._socks_conn.port)

    def connection_made(self, transport):
        self.transport = transport
        if len(transport.get_extra_info("sockname")) == 4:
            self.is_ipv6 = True
        else:
            self.is_ipv6 = False

    def _detect_source_ip_port(self, socket_addr, data):
        # Either proxy protocol is not enabled, or the packet is not from a
        # local source.
        if not self.proxy_protocol or not socket_addr[0].startswith("10."):
            source = Source(self, socket_addr, socket_addr[0], socket_addr[1])
            return source, data

        # If enabled, expect new connections to start with PROXY. In this
        # header is the original source of the connection.
        if data[0:5] != b"PROXY":
            # For existing connections, we should already know the mapping.
            # This is how for example nginx works, where only the first packet
            # of an UDP stream has the proxy protocol header, and no other
            # packets from the same source will.
            if socket_addr in self._mapping:
                return self._mapping[socket_addr], data

            raise NoProxyProtocol(
                f"Receive data without a proxy protocol header from {socket_addr[0]}:{socket_addr[1]}"
            )

        # This message arrived via the proxy protocol; use the information
        # from this to figure out the real ip and port.
        proxy_end = data.find(b"\r\n")
        proxy = data[0:proxy_end].decode()
        data = data[proxy_end + 2 :]

        # Example how 'proxy' looks:
        #  PROXY UDP4 127.0.0.1 127.0.0.1 33487 12345

        (_, _, ip, _, port, _) = proxy.split(" ")
        source = Source(self, socket_addr, ip, int(port))

        self._mapping[socket_addr] = source
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

    def send_packet(self, socket_addr, data, new_connection=False):
        if self.socks_proxy and new_connection:
            # Modify the packet to have a SOCKS header with relay information.
            data = self._socks_conn.prepare_udp_connection(socket_addr[0], socket_addr[1], data)

            response = asyncio.Future()
            protocol = SocksProtocol(data, response.set_result)

            # Prepare the coroutine to fire the packet. It is up to the caller
            # to await the results
            request = asyncio.get_event_loop().create_datagram_endpoint(lambda: protocol, remote_addr=self._socks_addr)
            return request, response

        self.transport.sendto(data, socket_addr)
        return None, None


@click_additional_options
@click.option(
    "--proxy-protocol",
    help="Enable Proxy Protocol (v1), and expect all incoming package to have this header.",
    is_flag=True,
)
@click.option(
    "--socks-proxy",
    help="Use a SOCKS proxy to query game servers.",
)
def click_proxy_protocol(proxy_protocol, socks_proxy):
    OpenTTDProtocolUDP.proxy_protocol = proxy_protocol
    OpenTTDProtocolUDP.socks_proxy = socks_proxy
