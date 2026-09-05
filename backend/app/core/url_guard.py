"""Outbound URL policy for the HTTP Request node.

A workflow author controls the URL a node calls, which makes the node a
server-side request forgery vector: without a policy it could be pointed at
``http://169.254.169.254/`` or at a service on the host's private network.

Every outbound URL is checked here before a connection is opened, and every
redirect hop is checked again, because a public host can redirect to a private
address.
"""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

#: Hostnames that resolve to the host itself often bypass naive IP checks.
BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata.goog",
    }
)

#: Cloud instance metadata services, which frequently need no authentication.
BLOCKED_NETWORKS = (
    ipaddress.ip_network("169.254.0.0/16"),  # link-local, includes 169.254.169.254
    ipaddress.ip_network("fe80::/10"),
)


class BlockedURLError(ValueError):
    """The requested URL is not allowed to be called."""


@dataclass(frozen=True, slots=True)
class URLPolicy:
    """How permissive outbound requests are allowed to be.

    Self-hosted deployments that genuinely need to reach an internal service
    can opt in, either wholesale or by naming specific hosts.
    """

    allow_private_networks: bool = False
    allowed_hosts: frozenset[str] = frozenset()

    def permits_host(self, hostname: str) -> bool:
        return hostname.lower() in self.allowed_hosts


def _is_blocked_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if any(address in network for network in BLOCKED_NETWORKS):
        return True
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def resolve_addresses(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve ``hostname`` to every address it currently maps to."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise BlockedURLError(f"Could not resolve host {hostname!r}.") from error

    return [ipaddress.ip_address(info[4][0]) for info in infos]


def assert_url_allowed(url: str, policy: URLPolicy) -> None:
    """Raise `BlockedURLError` unless ``url`` may be requested.

    The host is resolved and *every* address it maps to is checked, so a name
    with both a public and a private record cannot slip through.
    """
    parts = urlsplit(url)

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise BlockedURLError(
            f"Only http and https URLs can be requested, got {parts.scheme or 'no'} scheme."
        )

    hostname = parts.hostname
    if not hostname:
        raise BlockedURLError("The URL is missing a host.")

    if policy.permits_host(hostname):
        return

    if hostname.lower() in BLOCKED_HOSTNAMES and not policy.allow_private_networks:
        raise BlockedURLError(f"Requests to {hostname} are blocked.")

    # A literal IP needs no lookup, and must not be given one.
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        addresses = resolve_addresses(hostname)
    else:
        addresses = [literal]

    if policy.allow_private_networks:
        return

    for address in addresses:
        if _is_blocked_address(address):
            raise BlockedURLError(
                f"Requests to private or reserved addresses are blocked "
                f"({hostname} resolves to {address})."
            )
