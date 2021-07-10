import aioredis
import click
import hashlib
import ipaddress
import json
import logging

from openttd_helpers import click_helper

from .interface import DatabaseInterface

log = logging.getLogger(__name__)

_redis_url = None

# Servers should announce every 15 minutes, so if we haven't seen a server
# after 20 minutes, we can assume it is no longer running.
TTL = 60 * 20


def md5sum(value):
    return hashlib.md5(value.encode()).digest().hex()


def _get_server_id(server_ip, server_port):
    if isinstance(server_ip, ipaddress.IPv6Address):
        return md5sum(f"[{server_ip}]:{server_port}")
    else:
        return md5sum(f"{server_ip}:{server_port}")


class Database(DatabaseInterface):
    def __init__(self):
        self._redis = aioredis.from_url(_redis_url, decode_responses=True)

    async def check_session_key_token(self, session_key, token):
        ms_token = await self._redis.get(f"ms-session-key:{session_key}")
        if ms_token is None:
            return False

        if ms_token != str(token):
            return False

        await self._redis.expire(f"ms-session-key:{session_key}", TTL)
        return True

    async def store_session_key_token(self, session_key, token):
        await self._redis.set(f"ms-session-key:{session_key}", token, ex=TTL)

    async def server_online(self, session_key, server_ip, server_port, info):
        # Don't accept servers with empty revision or name.
        if info["openttd_version"] == "" or info["name"] == "":
            return False

        # server_offline() doesn't get the session_key, so we need a reverse lookup.
        await self._redis.set(f"ms-session-id:{server_ip}:{server_port}", session_key, ex=TTL)

        # Create a server-id based on the first ip/port we see of this server.
        # This means the server-id remains mostly stable between restarts.
        server_id = await self._redis.get(f"ms-server-id:{session_key}")
        if server_id is None:
            server_id = _get_server_id(server_ip, server_port)
        await self._redis.set(f"ms-server-id:{session_key}", server_id, ex=TTL)

        info["game_type"] = 1  # Public

        # Update the information of this server.
        info_str = json.dumps(info)
        await self._redis.set(f"gc-server:{server_id}", info_str, ex=TTL)
        await self._redis.xadd("gc-stream", {"gc-id": -1, "update": server_id, "info": info_str}, approximate=1000)

        # Track this IP based on the server_id.
        if isinstance(server_ip, ipaddress.IPv6Address):
            type = "ipv6"
        else:
            type = "ipv4"
        server_str = json.dumps({"ip": str(server_ip), "port": server_port})
        if await self._redis.set(f"gc-direct-{type}:{server_id}", server_str, ex=TTL) > 0:
            await self._redis.xadd(
                "gc-stream", {"gc-id": -1, f"new-direct-{type}": server_id, "server": server_str}, approximate=1000
            )

        return True

    async def server_offline(self, server_ip, server_port):
        # Find the session-key of this ip:port combination.
        session_key = await self._redis.get(f"ms-session-id:{server_ip}:{server_port}")
        if session_key is None:
            return
        await self._redis.delete(f"ms-session-id:{server_ip}:{server_port}")

        server_id = await self._redis.get(f"ms-server-id:{session_key}")
        if server_id is None:
            return
        await self._redis.delete(f"ms-server-id:{session_key}")

        await self._redis.delete(f"gc-direct-ipv4:{server_id}")
        await self._redis.delete(f"gc-direct-ipv6:{server_id}")

        # Delete this server.
        if await self._redis.delete(f"gc-server:{server_id}") > 0:
            await self._redis.xadd("gc-stream", {"gc-id": -1, "delete": server_id}, approximate=1000)

    async def get_server_list_for_client(self, ipv6_list):
        if ipv6_list:
            type = "ipv6"
            ipcls = ipaddress.IPv6Address
        else:
            type = "ipv4"
            ipcls = ipaddress.IPv4Address

        server_list = []
        direct_ips = await self._redis.keys(f"gc-direct-{type}:*")
        for direct_ip_key in direct_ips:
            direct_ip_str = await self._redis.get(direct_ip_key)
            direct_ip = json.loads(direct_ip_str)
            direct_ip["ip"] = ipcls(direct_ip["ip"])
            server_list.append(direct_ip)

        return server_list

    async def get_server_info_for_web(self, server_id):
        info_str = await self._redis.get(f"gc-server:{server_id}")
        entry = {
            "info": json.loads(info_str),
            "online": True,
        }

        direct_ipv4_str = await self._redis.get(f"gc-direct-ipv4:{server_id}")
        if direct_ipv4_str:
            direct_ipv4 = json.loads(direct_ipv4_str)
            entry["ipv4"] = {
                "ip": direct_ipv4["ip"],
                "port": direct_ipv4["port"],
                "server_id": server_id,
            }

        direct_ipv6_str = await self._redis.get(f"gc-direct-ipv6:{server_id}")
        if direct_ipv6_str:
            direct_ipv6 = json.loads(direct_ipv6_str)
            entry["ipv6"] = {
                "ip": direct_ipv6["ip"],
                "port": direct_ipv6["port"],
                "server_id": server_id,
            }

        return entry

    async def get_server_list_for_web(self):
        server_list = []

        servers = await self._redis.keys("gc-server:*")
        for server_key in servers:
            _, _, server_id = server_key.partition(":")
            entry = self.get_server_info_for_web(server_id)
            server_list.append(entry)

        return server_list

    def check_stale_servers(self):
        # Redis takes care of this for us.
        pass


@click_helper.extend
@click.option(
    "--redis-url",
    help="URL of the redis server.",
    default="redis://localhost",
)
def click_database_redis(redis_url):
    global _redis_url

    _redis_url = redis_url
