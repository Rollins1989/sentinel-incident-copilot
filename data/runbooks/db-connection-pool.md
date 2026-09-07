# Database Connection Pool Exhaustion

## Symptoms
- Application logs show `connection pool exhausted` or `timeout waiting for connection` errors.
- Elevated request latency correlated with traffic peaks.
- Database server itself shows normal CPU/memory (this is a client-side pooling issue, not a DB capacity issue).

## Diagnostic Steps
1. Check current pool utilization via the `/metrics` endpoint: look at `db_pool_active` vs `db_pool_max`.
2. Confirm whether the spike correlates with a traffic surge or with a recent slow query (a single slow query holding connections can exhaust the pool even at normal traffic).
3. Check for connection leaks: look for a rising `db_pool_active` count that never returns to baseline after traffic subsides.

## Remediation
1. If it's a traffic surge and the pool is undersized: increase `DB_POOL_MAX_SIZE` from its current value, in increments of 20%, and redeploy. Do not more than double it in one change — this can overwhelm the database itself.
2. If a leak is suspected: check recent code changes for connections acquired without a corresponding release (missing `finally`/context-manager block).
3. If a single slow query is holding connections: identify it via the slow query log and either add a missing index or set a statement timeout of 5 seconds on that query path.
4. As an immediate mitigation while investigating root cause, enable connection pool queueing with a max wait of 2 seconds so requests fail fast instead of piling up.

## Escalation
If pool exhaustion recurs across multiple services simultaneously, treat as a database-level incident rather than a single-service issue and escalate to the database on-call.
