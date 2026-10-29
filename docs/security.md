# Security model and limitations

Implemented controls:

- PBKDF2-HMAC-SHA256 with 600,000 iterations, random per-password salt, constant-time
  comparison, and dummy verification work for unknown accounts.
- Expiring signed HS256 bearer tokens with required issuer, audience, timestamps,
  subject and role; algorithm allowlist; no password hashes in API responses.
- Customer-only registration, explicit admin checks, owner-filtered orders/inbox.
- Separate generated internal-service secret and independent database credentials.
- No service credential forwarded by gateway. Internal endpoints stay private in
  Compose. Native development binds services to loopback.
- Integer money, strict quantities, duplicate-line rejection, bounded inputs.
- Browser tokens are memory-only; DOM content is created with textContent rather
  than untrusted innerHTML; restrictive CSP, frame denial, nosniff response headers.
- Non-root app containers, dropped capabilities, ignored credentials and data.
- Pinned dependency lock and CI vulnerability audit.

Threats still requiring work before public deployment:

- No TLS termination, distributed rate limiting, credential-stuffing protection,
  account verification, password reset, refresh tokens, or immediate token revocation.
- HS256 verification keys permit any holder to sign tokens. Use an external OIDC
  provider or asymmetric signing with isolated private keys for stronger trust boundaries.
- Internal authentication is a shared key, not mTLS or workload identity. Compose
  uses one network; compromise of a container can reach other internal APIs.
- Secrets live in local `.env`/container environment, not a managed secret store.
- No audited inventory adjustments, automatic pending-order recovery, reservation
  expiry, provider reconciliation, refunds, or cancellation lifecycle.
- Gateway checks body size after reading it; it is not streaming ingress protection.
  Add proxy-level request/concurrency limits before exposure.
- JSON aggregates provide limited database domain validation and query performance.
- No independent penetration test, image scan evidence, production backup restore
  drill, high-availability test, privacy policy, or retention controls.

Never enter real payment data. The payment model accepts only approve/decline.
Do not expose this local demo through public port forwarding.

Audit the lock with `pip-audit -r requirements.lock.txt --no-deps --disable-pip`
after installing the separately pinned audit tool used in CI. An audit with no
known findings is time-bound evidence, not proof of security. Vulnerability scans
must be repeated when dependencies or advisory data change.
