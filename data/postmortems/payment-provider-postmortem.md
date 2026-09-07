# Postmortem: Third-Party Payment Provider Incident

## Summary
A third-party payment provider experienced a regional outage, causing our
payment confirmation webhook to stop receiving callbacks. Orders were
accepted but confirmation emails were delayed by up to 3 hours. Total
resolution time from first alert to full recovery was 3 hours 12 minutes.

## Timeline
- 09:14 — Webhook delivery failures begin (provider-side outage).
- 09:26 — Alert fires on rising "pending confirmation" order count.
- 09:40 — Provider status page confirms regional outage.
- 10:15 — Manual reconciliation job started to poll the provider's API
  directly instead of waiting on webhooks.
- 12:26 — Provider outage resolved; webhook delivery resumes.
- 12:26 — Backlog of ~1,800 pending confirmations fully processed.

## Root Cause
Our system had no fallback path when webhook delivery failed — it depended
entirely on the provider's push notifications with no polling backstop.

## Follow-up Actions
1. Implement a polling fallback that activates automatically after 15
   minutes of webhook silence.
2. Add a dashboard alert specifically for "pending confirmation" order
   count exceeding 50, independent of webhook health.
3. Document the manual reconciliation procedure as a runbook so it doesn't
   depend on a specific engineer's memory of how to run it.
