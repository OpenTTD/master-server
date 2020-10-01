import asyncio
import ipaddress
import logging

log = logging.getLogger(__name__)


class Common:
    def __init__(self, retry_reached_callback=None):
        self._ms_mapping = {}
        self._retry_reached_callback = retry_reached_callback

    async def _query_server_task(self, protocol, ip, port, timeout, retry):
        # For an IPv4 socket, a tuple of two should be used. For IPv6 a tuple
        # of four. If an IPv4 address is sent over IPv6 socket, it should be
        # prefixed with "::ffff:".
        if protocol.is_ipv6:
            if isinstance(ip, ipaddress.IPv4Address):
                server_addr = (f"::ffff:{ip}", port, 0, 0)
            else:
                server_addr = (str(ip), port, 0, 0)
        else:
            server_addr = (str(ip), port)

        # Retry as often as requested. If a response is received, our task is
        # cancelled, so we don't have to worry about that.
        retry_left = retry
        while retry_left > 0:
            request, response = protocol.send_PACKET_UDP_CLIENT_FIND_SERVER(server_addr, new_connection=True)

            if request and response:

                async def send_via_socks():
                    transport, _ = await request
                    try:
                        data = await response
                        protocol.datagram_received(data, server_addr)
                    finally:
                        transport.close()

                # The SOCKS connection times out after 30 seconds; we want it
                # cancelled earlier, so we create a new task, and stop waiting
                # for it after our own timeout.
                task = asyncio.ensure_future(send_via_socks())
                try:
                    await asyncio.sleep(timeout)
                finally:
                    # Either we got cancelled or the timeout happened; either
                    # way, close up the UDP socket.
                    task.cancel()
            else:
                protocol.send_PACKET_UDP_CLIENT_FIND_SERVER(server_addr)
                await asyncio.sleep(timeout)

            retry_left -= 1

        # Forget about this query, as we consider it failed
        ms_key = (ip, port)
        del self._ms_mapping[ms_key]

        if self._retry_reached_callback:
            self._retry_reached_callback(ip, port)

    def query_server(self, ip, port, protocol, user_data=None, timeout=5, retry=3):
        # Check if we are already querying this server.
        # This can happen if we are flooded for example.
        ms_key = (ip, port)
        if ms_key in self._ms_mapping:
            return

        # Query the server in its own task.
        task = asyncio.ensure_future(self._query_server_task(protocol, ip, port, timeout, retry))

        # Keep a mapping of all servers we are querying, linking to their
        # task. This allows us to cancel the task if a response is received.
        self._ms_mapping[ms_key] = (task, user_data)

    def query_server_response(self, ip, port):
        # Check if we expected a response from this server.
        ms_key = (ip, port)
        task, user_data = self._ms_mapping.get(ms_key, (None, None))
        if not task:
            log.info("Response from %s:%d, but we did not expect a response.", ip, port)
            return None

        # Cancel the timeout timer, and make sure that any retransmit is
        # not being processed anymore.
        task.cancel()
        del self._ms_mapping[ms_key]

        return user_data
