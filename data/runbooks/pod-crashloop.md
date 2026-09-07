# Kubernetes Pod CrashLoopBackOff

## Symptoms
- Pods for a service repeatedly restart and enter `CrashLoopBackOff` state.
- `kubectl get pods` shows increasing `RESTARTS` count.
- Requests to the service intermittently return 502/503 as pods cycle.

## Diagnostic Steps
1. Check pod status and restart count: `kubectl get pods -n <namespace> -l app=<service>`.
2. Inspect the last container logs before the crash: `kubectl logs <pod> --previous`.
3. Check for `OOMKilled` in `kubectl describe pod <pod>` under the `Last State` section — this indicates a memory limit issue, not an application bug.
4. Check recent deploys: `kubectl rollout history deployment/<service>`. Most CrashLoopBackOff incidents immediately follow a deploy.
5. Verify readiness/liveness probe configuration — an overly aggressive liveness probe timeout can cause healthy-but-slow-starting pods to be killed before they finish initializing.

## Remediation
1. If `OOMKilled`: increase the memory limit in the deployment manifest by 25% and redeploy, then monitor for 15 minutes.
2. If tied to a recent deploy and logs show an application error (e.g. missing env var, failed migration): roll back immediately with `kubectl rollout undo deployment/<service>`.
3. If liveness probe is killing slow-starting pods: increase `initialDelaySeconds` on the liveness probe from its current value by at least 30 seconds.
4. Only restart the pod manually (`kubectl delete pod <pod>`) after confirming one of the above root causes — restarting without a fix just re-triggers the same crash loop.

## Escalation
If restarts continue after rollback and probe adjustment, escalate to the platform team — this may indicate a node-level resource pressure issue rather than an application issue.
