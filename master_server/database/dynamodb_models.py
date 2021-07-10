from pynamodb.models import Model
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    TTLAttribute,
    UnicodeAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from .dynamodb_attributes import (
    BinaryAttribute,
    BooleanAsNumberAttribute,
    IpAddressAttribute,
)


class ServerIpMap(MapAttribute):
    ip = IpAddressAttribute()
    port = NumberAttribute()

    def __eq__(self, other):
        return isinstance(other, ServerIpMap) and self.ip == other.ip and self.port == other.port

    def __repr__(self):
        return str(vars(self))


class GrfMap(MapAttribute):
    grfid = NumberAttribute()
    md5sum = BinaryAttribute()

    def __repr__(self):
        return str(vars(self))


class InfoMap(MapAttribute):
    newgrfs = ListAttribute(of=GrfMap)
    game_date = NumberAttribute()
    start_date = NumberAttribute()
    companies_max = NumberAttribute()
    companies_on = NumberAttribute()
    spectators_max = NumberAttribute()
    name = UnicodeAttribute()
    openttd_version = UnicodeAttribute()
    use_password = NumberAttribute()
    clients_max = NumberAttribute()
    clients_on = NumberAttribute()
    spectators_on = NumberAttribute()
    map_width = NumberAttribute()
    map_height = NumberAttribute()
    map_type = NumberAttribute()
    is_dedicated = NumberAttribute()

    def __repr__(self):
        return str(vars(self))


class Server(Model):
    class OnlineIndex(GlobalSecondaryIndex):
        class Meta:
            read_capacity_units = 3
            write_capacity_units = 3
            projection = AllProjection()

        online = BooleanAsNumberAttribute(hash_key=True)

    class TimeLastSeenIndex(GlobalSecondaryIndex):
        class Meta:
            read_capacity_units = 3
            write_capacity_units = 3
            projection = AllProjection()

        online = BooleanAsNumberAttribute(hash_key=True)
        time_last_seen = NumberAttribute(range_key=True)

    class Meta:
        table_name = "MSU-server"
        read_capacity_units = 3
        write_capacity_units = 3

    session_key = NumberAttribute(hash_key=True)
    token = NumberAttribute()

    online = BooleanAsNumberAttribute(default=False)
    online_view = OnlineIndex()

    ipv4 = ServerIpMap(null=True)
    ipv6 = ServerIpMap(null=True)
    info = InfoMap(null=True)

    time_first_seen = NumberAttribute(null=True)
    time_last_seen = NumberAttribute(null=True)
    time_last_seen_view = TimeLastSeenIndex()

    ttl = TTLAttribute()

    def __repr__(self):
        return str(vars(self))


class IpPort(Model):
    class OnlineIndex(GlobalSecondaryIndex):
        class Meta:
            read_capacity_units = 3
            write_capacity_units = 3
            projection = AllProjection()

        online = BooleanAsNumberAttribute(hash_key=True)

    class TimeLastSeenIndex(GlobalSecondaryIndex):
        class Meta:
            read_capacity_units = 3
            write_capacity_units = 3
            projection = AllProjection()

        online = BooleanAsNumberAttribute(hash_key=True)
        time_last_seen = NumberAttribute(range_key=True)

    class Meta:
        table_name = "MSU-ip-port"
        read_capacity_units = 3
        write_capacity_units = 3

    server_id = UnicodeAttribute(hash_key=True)
    session_key = NumberAttribute()

    server_ip = ServerIpMap()

    online = BooleanAsNumberAttribute(default=False)
    online_view = OnlineIndex()

    time_last_seen = NumberAttribute(null=True)
    time_last_seen_view = TimeLastSeenIndex()

    ttl = TTLAttribute()

    def __repr__(self):
        return str(vars(self))
