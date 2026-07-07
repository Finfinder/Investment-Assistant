"""Client identity resolution for rate limiting and proxy-aware IP extraction.

This module centralizes how the application identifies a client for rate
limiting purposes. It defends against ``X-Forwarded-For`` header spoofing by
only trusting that header when the request originates from a configured trusted
proxy, and prefers an authenticated JWT subject over IP-based identification
when available.
"""

import ipaddress
import logging
from collections.abc import Mapping
from functools import lru_cache

from fastapi import HTTPException, Request

from app.core.auth import verify_token
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Header carrying the original client chain behind proxies (IETF standard).
_X_FORWARDED_FOR = "x-forwarded-for"

# Union of concrete network types (avoids private _BaseNetwork generic args).
NetworkType = ipaddress.IPv4Network | ipaddress.IPv6Network


@lru_cache(maxsize=1)
def _get_trusted_proxies() -> tuple[NetworkType, ...]:
    """Parse configured trusted proxy CIDRs into a cached tuple of networks."""
    settings = get_settings()
    return tuple(ipaddress.ip_network(entry, strict=False) for entry in settings.TRUSTED_PROXIES)


def _is_trusted_peer(peer: str, trusted: tuple[NetworkType, ...]) -> bool:
    """Return True if the direct peer address belongs to a trusted proxy network."""
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(addr in network for network in trusted)


def _is_valid_ip(value: str) -> bool:
    """Return True if the value is a parseable IP address (v4 or v6)."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def resolve_client_ip(
    headers: Mapping[str, str],
    direct_peer: str,
    *,
    trusted_proxies: tuple[NetworkType, ...] | None = None,
) -> tuple[str, bool]:
    """Resolve the originating client IP from proxy headers with spoofing checks.

    Args:
        headers: Incoming request headers (case-insensitive lookup).
        direct_peer: The direct TCP peer address (``request.client.host``).
        trusted_proxies: Optional pre-parsed trusted networks. When omitted, the
            configured ``TRUSTED_PROXIES`` setting is used.

    Returns:
        A tuple of ``(client_ip, spoofing_suspected)`` where ``client_ip`` is the
        resolved identifier and ``spoofing_suspected`` flags a potentially forged
        ``X-Forwarded-For`` chain.
    """
    if trusted_proxies is None:
        trusted_proxies = _get_trusted_proxies()

    xff = headers.get(_X_FORWARDED_FOR)
    if not xff:
        return direct_peer, False

    # Split into hops, trimming whitespace and dropping empty entries.
    hops = [hop.strip() for hop in xff.split(",") if hop.strip()]
    if not hops:
        return direct_peer, False

    # Without trusted proxies the header is fully attacker-controlled: ignore it.
    if not trusted_proxies:
        return direct_peer, True

    # Only trust the header when the request actually comes from a trusted proxy.
    # An attacker connecting directly (untrusted peer) could forge the chain to
    # impersonate another client, so we must reject XFF unless the peer is trusted.
    if not _is_trusted_peer(direct_peer, trusted_proxies):
        return direct_peer, True

    # Walk from the rightmost hop (closest to us) and skip trusted proxy hops.
    # The first untrusted hop from the right that is a *valid* IP address is the
    # originating client. Hops that are not valid IPs are attacker-controlled junk
    # (e.g. "attacker-controlled"): they must never become the rate-limit key, so
    # we flag spoofing and fall back to the direct peer instead of trusting them.
    client_ip = direct_peer
    spoofing_suspected = False
    for hop in reversed(hops):
        if _is_trusted_peer(hop, trusted_proxies):
            continue
        if not _is_valid_ip(hop):
            # Invalid hop cannot be a real client IP -> treat as spoofing.
            spoofing_suspected = True
            break
        client_ip = hop
        spoofing_suspected = False
        break
    else:
        # Every hop was a trusted proxy; fall back to the direct peer.
        client_ip = direct_peer

    # NOTE: chain length is intentionally NOT used as a spoofing signal.
    # ``len(trusted_proxies)`` counts configured CIDR *rules*, not the number of
    # physical proxy hops - a single broad CIDR (e.g. 10.0.0.0/8) can cover many
    # proxy layers, while several narrow /32 rules inflate the threshold without
    # adding real depth. Either way the comparison is meaningless, so a long
    # chain behind a legitimate proxy topology must not be flagged as spoofing.
    # Spoofing is instead detected by the hop-by-hop membership validation above:
    # we walk from the right, trust only hops inside ``trusted_proxies``, and the
    # first untrusted valid IP becomes the client. Anything further left is
    # client-appended and simply ignored, so its presence neither changes the
    # resolved client IP nor indicates an attack. The remaining spoofing signals
    # are: no trusted proxies configured, an untrusted direct peer, or a
    # non-IP (junk) hop in the chain.

    return client_ip, spoofing_suspected


def get_rate_limit_key(request: Request) -> str:
    """Return the rate-limit key for a request.

    Prefers the authenticated JWT subject (``user:<sub>``) when a valid Bearer
    token is present, otherwise falls back to the proxy-aware client IP.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[len("bearer ") :].strip()
        try:
            token_data = verify_token(token)
            return f"user:{token_data.sub}"
        except HTTPException:
            # Invalid/expired token (per verify_token contract): do not leak
            # identity, fall through to IP-based rate limiting.
            logger.debug("Rate-limit key: invalid Bearer token, falling back to IP")
        except Exception:
            # Unexpected failure (e.g. misconfiguration, future refactor bug):
            # log it so monitoring can alert, but keep graceful degradation to IP
            # instead of propagating and returning 500 on every authorized request.
            logger.exception("Rate-limit key: unexpected error verifying token, falling back to IP")

    direct_peer = request.client.host if request.client else "127.0.0.1"
    client_ip, spoofing_suspected = resolve_client_ip(request.headers, direct_peer)
    if spoofing_suspected:
        xff = request.headers.get(_X_FORWARDED_FOR, "")
        last_hop = [h.strip() for h in xff.split(",") if h.strip()][-1] if xff else direct_peer
        logger.warning(
            "Possible X-Forwarded-For spoofing: %d hops, last hop %s",
            len([h for h in xff.split(",") if h.strip()]),
            last_hop,
        )
    return client_ip
