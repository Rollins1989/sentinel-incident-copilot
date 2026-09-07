# Internal Notifications API

## Overview
Handles email, SMS, and push notification delivery for all internal
services. Backed by a queue with automatic retry on transient failures.

## Retry Behavior
Failed deliveries are retried with exponential backoff starting at 2
seconds, doubling each attempt, up to a **maximum backoff of 5 minutes**
between attempts. After 8 total attempts, the notification is moved to the
dead-letter queue and an alert fires.

## Endpoints
- `POST /v1/notify` — send a notification. Body requires `channel`, `recipient`, `template_id`.
- `GET /v1/notify/{id}/status` — check delivery status of a queued notification.

## Rate Limits
Callers are limited to 500 requests per minute per service API key. Exceeding
this returns `429` with a `Retry-After` header.
