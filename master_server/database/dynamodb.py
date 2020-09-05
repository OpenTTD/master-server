import hashlib
import ipaddress
import logging

from datetime import (
    datetime,
    timedelta,
)
from inspect import getmembers
from pynamodb.attributes import Attribute

from .dynamodb_models import (
    IpPort,
    ServerIpMap,
    InfoMap,
    Server,
)
from .interface import DatabaseInterface

log = logging.getLogger(__name__)

# After 20 minutes with no advertisement, mark servers as stale.
STALE_SERVER_TIMEOUT = 60 * 20
# When database entries expire. A server after 20 minutes is marked offline;
# so 60 minutes is a safe value.
TTL = 60 * 60


def md5sum(value):
    return hashlib.md5(value.encode()).digest().hex()


def _get_server_id(server_ip, server_port):
    if isinstance(server_ip, ipaddress.IPv6Address):
        return md5sum(f"[{server_ip}]:{server_port}")
    else:
        return md5sum(f"{server_ip}:{server_port}")


def _convert_server_to_dict(server):
    entry = {
        "info": {},
        "time_first_seen": server.time_first_seen,
        "time_last_seen": server.time_last_seen,
        "online": server.online,
    }

    if server.ipv4:
        entry["ipv4"] = {
            "ip": str(server.ipv4.ip),
            "port": server.ipv4.port,
            "server_id": _get_server_id(server.ipv4.ip, server.ipv4.port),
        }
    if server.ipv6:
        entry["ipv6"] = {
            "ip": str(server.ipv6.ip),
            "port": server.ipv6.port,
            "server_id": _get_server_id(server.ipv6.ip, server.ipv6.port),
        }

    for name, _ in getmembers(InfoMap, lambda o: isinstance(o, Attribute)):
        if name == "grfs":
            entry["info"]["grfs"] = [
                {
                    "grfid": grf["grfid"],
                    "md5sum": grf["md5sum"].hex(),
                }
                for grf in getattr(server.info, name)
            ]
        else:
            entry["info"][name] = getattr(server.info, name)

    return entry


class Database(DatabaseInterface):
    def _update_ip_port(self, server_id, session_key):
        try:
            ip_port = IpPort.get(server_id)
            if ip_port.session_key == session_key:
                return

            # This IP:port is already known under another session-key.
            # Most likely this means the server never unregistered itself
            # (due to a server-crash for example). This means we can now
            # consider the original server offline, and this new key will
            # track the new server again.
            Server(ip_port.session_key).update(
                actions=[Server.online.set(False)],
                condition=Server.session_key == ip_port.session_key,
            )
        except IpPort.DoesNotExist:
            pass

    def __init__(self, host, region):
        # PynamoDB only allows to set these fields statically, while it is
        # much more likely you would like them dynamically. So .. we just
        # overwrite the fields. Sadly, this needs to be done per model, making
        # this a bit annoying to maintain.
        for model in (Server, IpPort):
            model.Meta.host = host
            model.Meta.region = region

            if not model.exists():
                model.create_table(wait=True)

    def check_session_key_token(self, session_key, token):
        try:
            server = Server.get(session_key)
        except Server.DoesNotExist:
            return False
        return server.token == token

    def store_session_key_token(self, session_key, token):
        server = Server(session_key, token=token, ttl=timedelta(seconds=TTL))
        server.save()

    def server_online(self, session_key, server_ip, server_port, info):
        server_id = _get_server_id(server_ip, server_port)
        self._update_ip_port(server_id, session_key)

        try:
            server = Server.get(session_key)
        except Server.DoesNotExist:
            return False

        # Update the server information.
        actions = [
            Server.info.set(InfoMap(**info)),
            Server.online.set(True),
            Server.time_last_seen.set(datetime.utcnow().timestamp()),
            Server.ttl.set(timedelta(seconds=TTL)),
        ]

        if server.time_first_seen is None:
            actions.append(Server.time_first_seen.set(datetime.utcnow().timestamp()))

        server_ip_map = ServerIpMap(ip=server_ip, port=server_port)
        field = "ipv6" if isinstance(server_ip, ipaddress.IPv6Address) else "ipv4"
        if getattr(server, field) != server_ip_map:
            actions.append(getattr(Server, field).set(server_ip_map))

        server.update(actions=actions, condition=Server.session_key == session_key)
        IpPort(
            server_id=server_id,
            session_key=session_key,
            online=True,
            server_ip=server_ip_map,
            time_last_seen=datetime.utcnow().timestamp(),
            ttl=timedelta(seconds=TTL),
        ).save()

        return True

    def server_offline(self, server_ip, server_port):
        server_id = _get_server_id(server_ip, server_port)

        # Lookup the session-key based on the ip/port.
        try:
            ip_port = IpPort.get(server_id)
        except IpPort.DoesNotExist:
            return

        Server(ip_port.session_key).update(
            actions=[
                Server.online.set(False),
                Server.time_last_seen.set(datetime.utcnow().timestamp()),
                Server.ttl.set(timedelta(seconds=TTL)),
            ],
            condition=Server.session_key == ip_port.session_key,
        )
        ip_port.update(
            actions=[
                IpPort.online.set(False),
                IpPort.time_last_seen.set(datetime.utcnow().timestamp()),
                IpPort.ttl.set(timedelta(seconds=TTL)),
            ]
        )

    def get_server_list_for_client(self, ipv6_list):
        server_list = []

        for ip_port in IpPort.online_view.query(True):
            if ipv6_list != isinstance(ip_port.server_ip.ip, ipaddress.IPv6Address):
                continue

            server_list.append(
                {
                    "ip": ip_port.server_ip.ip,
                    "port": ip_port.server_ip.port,
                }
            )

        return server_list

    def get_server_info_for_web(self, server_id):
        try:
            ip_port = IpPort.get(server_id)
        except IpPort.DoesNotExist:
            return None

        try:
            server = Server.get(ip_port.session_key)
        except Server.DoesNotExist:
            return None

        return _convert_server_to_dict(server)

    def get_server_list_for_web(self):
        return [_convert_server_to_dict(server) for server in Server.online_view.query(True)]

    def check_stale_servers(self):
        for server in Server.time_last_seen_view.query(
            True, Server.time_last_seen < datetime.utcnow().timestamp() - STALE_SERVER_TIMEOUT
        ):
            server.update(actions=[Server.online.set(False), Server.ttl.set(timedelta(seconds=TTL))])

        for ip_port in IpPort.time_last_seen_view.query(
            True, Server.time_last_seen < datetime.utcnow().timestamp() - STALE_SERVER_TIMEOUT
        ):
            ip_port.update(actions=[IpPort.online.set(False), IpPort.ttl.set(timedelta(seconds=TTL))])
