# Postmortem: Checkout Service Outage (Q2)

## Summary
The checkout service experienced a full outage for 47 minutes, blocking all
purchases. Root cause was a database migration that added a NOT NULL column
without a default value, which locked the `orders` table during a peak
traffic window.

## Timeline
- 14:02 — Migration deployed as part of routine release.
- 14:03 — `orders` table lock detected; write queries began timing out.
- 14:05 — Checkout error rate crossed alert threshold; on-call paged.
- 14:19 — Root cause identified as the migration's table lock.
- 14:41 — Migration rolled back; table lock released.
- 14:49 — Checkout service fully recovered; error rate returned to baseline.

## Root Cause
Adding a `NOT NULL` column without a default forces a full table rewrite on
the database engine in use, which takes an exclusive lock for the duration.
On a large `orders` table, this lock held long enough to exhaust the
checkout service's database connection pool.

## Follow-up Actions
1. Add a migration linter to CI that rejects `NOT NULL` columns without a
   default value on tables above a configured row-count threshold.
2. Require all schema migrations on high-traffic tables to be reviewed by
   the database on-call before merge.
3. Add a runbook entry (see `db-connection-pool.md`) cross-referencing this
   postmortem for future connection-pool-exhaustion incidents caused by
   locking migrations specifically.
