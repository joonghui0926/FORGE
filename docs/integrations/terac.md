# Terac integration contract status

Terac is the first external operating step: it turns an approved FORGE collection plan
into qualified worker assignments and rights-cleared submissions.

## Confirmed FORGE boundary

- Render Workflows, not Band, creates the Terac campaign.
- The request carries a correlation ID and idempotency key.
- Terac submissions enter FORGE through the signed `/webhooks/terac` endpoint.
- R2, not Terac, is the durable source of truth for raw media and consent artifacts.

## Provider details still to confirm

- Native campaign/task creation: REST API, MCP, or the current authenticated bridge.
- External upload URL support versus direct FORGE presigned upload.
- Submission delivery: webhook push, polling, or both.
- Worker consent and derivative-rights metadata fields.
- Expert/general-worker qualification fields.
- Reject, rework, and compensation API surface.
- Native webhook signature format.

Until those fields are confirmed, `TeracCampaignClient` uses the versioned bridge contract
and fails closed when the bridge URL or token is absent.
