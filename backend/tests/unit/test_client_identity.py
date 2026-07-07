"""Unit tests for client identity resolution (rate limiting anti-spoofing)."""

import ipaddress
from unittest.mock import MagicMock

from fastapi import Request

from app.core.client_identity import get_rate_limit_key, resolve_client_ip


def _net(cidr: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    return ipaddress.ip_network(cidr, strict=False)


def _headers(**kwargs: str) -> dict[str, str]:
    return {k.lower(): v for k, v in kwargs.items()}


# ---------------------------------------------------------------------------
# resolve_client_ip
# ---------------------------------------------------------------------------


def test_resolve_client_ip_no_xff_returns_peer() -> None:
    ip, suspected = resolve_client_ip(_headers(), "203.0.113.5")
    assert ip == "203.0.113.5"
    assert suspected is False


def test_resolve_client_ip_empty_xff_returns_peer() -> None:
    ip, suspected = resolve_client_ip(_headers(**{"X-Forwarded-For": "   "}), "203.0.113.5")
    assert ip == "203.0.113.5"
    assert suspected is False


def test_resolve_client_ip_spoofed_xff_without_trusted_proxies() -> None:
    # No trusted proxies configured: header is fully attacker-controlled.
    headers = _headers(**{"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
    ip, suspected = resolve_client_ip(headers, "203.0.113.5", trusted_proxies=())
    assert ip == "203.0.113.5"
    assert suspected is True


def test_resolve_client_ip_trusted_proxy_uses_rightmost_untrusted() -> None:
    # Rightmost hop is the trusted proxy; the client is the hop before it.
    trusted = (_net("10.0.0.0/8"),)
    headers = _headers(**{"X-Forwarded-For": "198.51.100.23, 10.0.0.1"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "198.51.100.23"
    assert suspected is False


def test_resolve_client_ip_all_hops_trusted_falls_back_to_peer() -> None:
    trusted = (_net("10.0.0.0/8"), _net("192.168.0.0/16"))
    headers = _headers(**{"X-Forwarded-For": "10.0.0.1, 192.168.0.5"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "10.0.0.1"
    assert suspected is False


def test_resolve_client_ip_long_chain_behind_trusted_proxy_not_flagged() -> None:
    trusted = (_net("10.0.0.0/8"),)
    # A single broad CIDR can cover many proxy layers, so a long chain behind a
    # trusted proxy is legitimate and must NOT be flagged as spoofing. The
    # rightmost untrusted hop (203.0.113.9) is the originating client.
    headers = _headers(**{"X-Forwarded-For": "198.51.100.23, 203.0.113.9, 10.0.0.1"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "203.0.113.9"
    assert suspected is False


def test_resolve_client_ip_single_untrusted_hop_no_spoof_flag() -> None:
    trusted = (_net("10.0.0.0/8"),)
    headers = _headers(**{"X-Forwarded-For": "198.51.100.23"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "198.51.100.23"
    assert suspected is False


def test_resolve_client_ip_untrusted_peer_ignores_xff() -> None:
    # Attacker connects directly (untrusted peer) and forges a chain that ends
    # with a trusted network hop to impersonate the victim. The header must be
    # ignored because the direct peer is not a trusted proxy.
    trusted = (_net("10.0.0.0/8"),)
    headers = _headers(**{"X-Forwarded-For": "198.51.100.23, 10.0.0.1"})
    ip, suspected = resolve_client_ip(headers, "9.9.9.9", trusted_proxies=trusted)
    assert ip == "9.9.9.9"
    assert suspected is True


def test_resolve_client_ip_trusted_peer_with_untrusted_first_hop() -> None:
    # Request comes from a trusted proxy; the rightmost untrusted hop is the client.
    trusted = (_net("10.0.0.0/8"),)
    headers = _headers(**{"X-Forwarded-For": "198.51.100.23, 10.0.0.1"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "198.51.100.23"
    assert suspected is False


def test_resolve_client_ip_invalid_hop_not_used_as_client() -> None:
    # Behind a trusted proxy, an attacker sends a non-IP junk hop
    # (e.g. "attacker-controlled, 10.0.0.1"). The junk hop must NOT become the
    # rate-limit key; we fall back to the direct peer and flag spoofing.
    trusted = (_net("10.0.0.0/8"),)
    headers = _headers(**{"X-Forwarded-For": "attacker-controlled, 10.0.0.1"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "10.0.0.1"
    assert suspected is True


def test_resolve_client_ip_all_hops_invalid_flags_spoofing() -> None:
    # All hops are junk (no valid IP at all): never return attacker-controlled
    # string; fall back to the direct peer and flag spoofing.
    trusted = (_net("10.0.0.0/8"),)
    headers = _headers(**{"X-Forwarded-For": "foo, bar, baz"})
    ip, suspected = resolve_client_ip(headers, "10.0.0.1", trusted_proxies=trusted)
    assert ip == "10.0.0.1"
    assert suspected is True


# ---------------------------------------------------------------------------
# get_rate_limit_key
# ---------------------------------------------------------------------------


def _make_request(headers: dict[str, str], client_host: str = "203.0.113.5") -> MagicMock:
    # FastAPI request headers are case-insensitive; emulate with lowercase keys.
    request = MagicMock(spec=Request)
    request.headers = {k.lower(): v for k, v in headers.items()}
    client = MagicMock()
    client.host = client_host
    request.client = client
    return request


def test_get_rate_limit_key_prefers_valid_jwt(monkeypatch) -> None:
    from app.core import client_identity

    captured = {}

    def fake_verify(token: str):
        captured["token"] = token
        return MagicMock(sub="alice")

    monkeypatch.setattr(client_identity, "verify_token", fake_verify)
    request = _make_request({"Authorization": "Bearer sample.jwt.token"})
    assert get_rate_limit_key(request) == "user:alice"
    assert captured["token"] == "sample.jwt.token"  # noqa: S105


def test_get_rate_limit_key_invalid_jwt_falls_back_to_ip(monkeypatch) -> None:
    from app.core import client_identity

    def fake_verify(token: str):
        raise ValueError("bad token")

    monkeypatch.setattr(client_identity, "verify_token", fake_verify)
    request = _make_request({"Authorization": "Bearer bad"}, client_host="203.0.113.9")
    assert get_rate_limit_key(request) == "203.0.113.9"


def test_get_rate_limit_key_no_auth_uses_peer(monkeypatch) -> None:
    from app.core import client_identity

    called = {"verify": False}

    def fake_verify(token: str):
        called["verify"] = True
        raise ValueError("unreachable")

    monkeypatch.setattr(client_identity, "verify_token", fake_verify)
    request = _make_request({}, client_host="203.0.113.7")
    assert get_rate_limit_key(request) == "203.0.113.7"
    assert called["verify"] is False


def test_get_rate_limit_key_spoofed_xff_without_trusted_logs_warning(monkeypatch, caplog) -> None:
    import logging

    from app.core import client_identity

    monkeypatch.setattr(client_identity, "verify_token", lambda t: (_ for _ in ()).throw(ValueError()))
    request = _make_request({"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}, client_host="203.0.113.7")
    with caplog.at_level(logging.WARNING):
        assert get_rate_limit_key(request) == "203.0.113.7"
    assert any("spoofing" in r.message.lower() for r in caplog.records)
