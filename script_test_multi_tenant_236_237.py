import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: object


def _request_json(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> HttpResponse:
    data = None
    hdrs: dict[str, str] = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
        return HttpResponse(status=200, body=json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if hasattr(e, "read") else ""
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"raw": raw}
        return HttpResponse(status=int(e.code), body=payload)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(msg)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _health_ok(base: str) -> None:
    r = _request_json(f"{base}/health")
    _assert(r.status == 200 and isinstance(r.body, dict) and r.body.get("status") == "ok", f"health failed: {r}")


def _dev_token(base: str, *, email: str, name: str, tenant_id: int | None = None) -> dict:
    body: dict = {"email": email, "name": name}
    if tenant_id is not None:
        body["tenant_id"] = int(tenant_id)
    r = _request_json(f"{base}/auth/dev/token", method="POST", body=body)
    _assert(r.status == 200 and isinstance(r.body, dict), f"dev/token failed: status={r.status} body={r.body}")
    return r.body


def _switch_tenant(base: str, *, token: str, tenant_id: int) -> str:
    r = _request_json(
        f"{base}/auth/switch-tenant",
        method="POST",
        body={"tenant_id": int(tenant_id)},
        headers=_auth_header(token),
    )
    _assert(r.status == 200 and isinstance(r.body, dict), f"switch-tenant failed: status={r.status} body={r.body}")
    t = r.body.get("access_token")
    _assert(bool(t), f"switch-tenant returned no token: {r.body}")
    return str(t)


def _create_tenant(base: str, *, token: str, slug: str) -> int:
    r = _request_json(
        f"{base}/tenant",
        method="POST",
        body={"name": f"Tenant {slug}", "slug": slug, "timezone": "UTC"},
        headers=_auth_header(token),
    )
    _assert(r.status in {200, 201} and isinstance(r.body, dict), f"create tenant failed: status={r.status} body={r.body}")
    return int(r.body["id"])


def _me(base: str, *, token: str) -> dict:
    r = _request_json(f"{base}/me", headers=_auth_header(token))
    _assert(r.status == 200 and isinstance(r.body, dict), f"/me failed: status={r.status} body={r.body}")
    return r.body


def _invite(base: str, *, token: str, tenant_id: int, email: str) -> int:
    r = _request_json(
        f"{base}/tenant/{tenant_id}/invite",
        method="POST",
        body={"email": email, "role": "user"},
        headers=_auth_header(token),
    )
    _assert(r.status in {200, 201} and isinstance(r.body, dict), f"invite failed: status={r.status} body={r.body}")
    _assert(r.body.get("status") == "PENDING", f"invite status expected PENDING, got: {r.body}")
    return int(r.body["membership_id"])


def _list_invites(base: str, *, token: str) -> list[dict]:
    r = _request_json(f"{base}/auth/invites", headers=_auth_header(token))
    _assert(r.status == 200 and isinstance(r.body, list), f"list invites failed: status={r.status} body={r.body}")
    return r.body


def _accept_invite(base: str, *, token: str, membership_id: int) -> dict:
    r = _request_json(
        f"{base}/auth/invites/{membership_id}/accept",
        method="POST",
        body={},
        headers=_auth_header(token),
    )
    _assert(r.status == 200 and isinstance(r.body, dict), f"accept failed: status={r.status} body={r.body}")
    _assert(r.body.get("status") == "ACTIVE", f"accept expected ACTIVE, got: {r.body}")
    return r.body


def _job_ping(base: str, *, token: str) -> int:
    r = _request_json(f"{base}/job/ping", method="POST", body={}, headers=_auth_header(token))
    _assert(r.status in {200, 201} and isinstance(r.body, dict), f"job/ping failed: status={r.status} body={r.body}")
    return int(r.body["job_id"])


def _job_get(base: str, *, token: str, job_id: int) -> HttpResponse:
    return _request_json(f"{base}/job/{job_id}", headers=_auth_header(token))


def main() -> int:
    parser = argparse.ArgumentParser(description="Teste 2.3.6/2.3.7: multi-tenant + convites + selection + isolamento")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--prefix", default="script_test_236_237")
    args = parser.parse_args()

    base = str(args.base_url).rstrip("/")
    prefix = str(args.prefix).strip() or "script_test_236_237"
    ts = int(time.time())

    _health_ok(base)

    inviter_email = f"{prefix}_inviter_{ts}@local"
    invitee_email = f"{prefix}_invitee_{ts}@local"

    print("[1] inviter dev/token (should issue token)")
    inviter_resp = _dev_token(base, email=inviter_email, name="Inviter")
    _assert("access_token" in inviter_resp, f"expected access_token for inviter: {inviter_resp}")
    inviter_token_default = str(inviter_resp["access_token"])

    print("[2] create tenant A and switch inviter to tenant A (admin)")
    tenant_a = _create_tenant(base, token=inviter_token_default, slug=f"{prefix}-a-{ts}")
    inviter_token_a = _switch_tenant(base, token=inviter_token_default, tenant_id=tenant_a)
    me_a = _me(base, token=inviter_token_a)
    _assert(int(me_a.get("tenant_id") or 0) == tenant_a, f"inviter tenant mismatch: {me_a}")
    _assert(me_a.get("role") == "admin", f"inviter role expected admin, got {me_a.get('role')}")

    print("[3] invitee dev/token (creates default ACTIVE membership)")
    invitee_resp = _dev_token(base, email=invitee_email, name="Invitee")
    _assert("access_token" in invitee_resp, f"expected access_token for invitee: {invitee_resp}")
    invitee_token_default = str(invitee_resp["access_token"])
    me_default = _me(base, token=invitee_token_default)
    tenant_default = int(me_default["tenant_id"])

    print("[4] inviter invites invitee to tenant A; invitee sees invite and accepts")
    membership_id = _invite(base, token=inviter_token_a, tenant_id=tenant_a, email=invitee_email)
    invites = _list_invites(base, token=invitee_token_default)
    _assert(any(int(i.get("membership_id") or 0) == membership_id for i in invites), f"invite not listed: invites={invites}")
    _accept_invite(base, token=invitee_token_default, membership_id=membership_id)

    print("[5] invitee now has 2 ACTIVE tenants -> dev/token without tenant_id must require selection")
    invitee_resp2 = _dev_token(base, email=invitee_email, name="Invitee")
    _assert(invitee_resp2.get("requires_tenant_selection") is True, f"expected requires_tenant_selection: {invitee_resp2}")
    _assert(len(invitee_resp2.get("tenants") or []) >= 2, f"expected >=2 tenants in response: {invitee_resp2}")

    print("[6] isolation: job created in tenant A cannot be read from default tenant token")
    job_id = _job_ping(base, token=inviter_token_a)
    r = _job_get(base, token=inviter_token_default, job_id=job_id)
    _assert(r.status == 403, f"expected 403 reading tenant-A job from default token, got {r.status} body={r.body}")
    r2 = _job_get(base, token=inviter_token_a, job_id=job_id)
    _assert(r2.status == 200, f"expected 200 reading job from correct tenant, got {r2.status} body={r2.body}")

    print("OK: multi-tenant regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

