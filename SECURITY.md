# Security policy

## Reporting

Do not include credentials, private account information or exploit details in a public issue.

For a suspected exposed credential, revoke or rotate it first through the owning platform. Then provide only the minimum non-secret evidence needed to identify the affected file, route or deployment.

## Supported release

Only the current production release at https://nasa-data-hub.vercel.app is actively supported.

## Security properties

NASA Data Hub is designed to preserve these properties:

1. The browser never receives `NASA_API_KEY`.
2. The serverless route is allow-listed and cannot act as an arbitrary proxy.
3. Credential-shaped query parameters are removed recursively from returned public payloads.
4. EONET requests never receive the NASA credential.
5. Shared links contain only allow-listed public filters.
6. Upstream content is rendered without unsafe HTML insertion.
7. Errors and health responses are not cached.
8. Production releases originate from verified merged source and retain a rollback path.

The in-memory courtesy limiter is not a distributed firewall. Platform-level firewall and bot controls remain necessary for coordinated abuse protection.
