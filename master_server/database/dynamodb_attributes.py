import ipaddress

from base64 import b64decode
from pynamodb.constants import (
    BINARY,
    DEFAULT_ENCODING,
    NUMBER,
    STRING,
)
from pynamodb.attributes import Attribute


class BinaryAttribute(Attribute):
    """
    A binary attribute (fixing base64 issue with core BinaryAttribute)
    """

    attr_type = BINARY

    def serialize(self, value):
        """
        Returns a binary string (boto3 does the base64 encoding)
        """
        return value

    def deserialize(self, value):
        """
        Returns a decoded string from base64
        """
        try:
            return b64decode(value.decode(DEFAULT_ENCODING))
        except AttributeError:
            return b64decode(value)


class BooleanAsNumberAttribute(Attribute):
    """
    A class for boolean stored as Number attribute
    """

    attr_type = NUMBER

    def serialize(self, value):
        if value is None:
            return None
        elif value:
            return "1"
        else:
            return "0"

    def deserialize(self, value):
        return bool(int(value))


class IpAddressAttribute(Attribute):
    """
    A class for IpAddress stored as String attribute
    """

    attr_type = STRING

    def serialize(self, value):
        if isinstance(value, ipaddress.IPv4Address) or isinstance(value, ipaddress.IPv6Address):
            return str(value)
        raise ValueError("ipaddress must be of type ipaddress.IPv[46]Address")

    def deserialize(self, value):
        if ":" in value:
            return ipaddress.IPv6Address(value)
        else:
            return ipaddress.IPv4Address(value)
