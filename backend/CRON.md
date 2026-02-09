# Cron: Auto-create posts from trends

Trigger the automation endpoint on a schedule so draft posts are created from trending topics for users who have automation enabled.

## Full endpoint URL

- **Base:** `https://synovora-geotechcompany-us.onrender.com`
- **Endpoint:** `/cron/run-automation`
- **Full URL (GET or POST):**  
  **`https://synovora-geotechcompany-us.onrender.com/cron/run-automation`**

Use this URL in [cron-job.org](https://cron-job.org), Render Cron, GitHub Actions, or system cron.

## cron-job.org setup

1. Go to [cron-job.org](https://cron-job.org) and create or sign in to your account.
2. Create a new cron job.
3. **URL:** `https://synovora-geotechcompany-us.onrender.com/cron/run-automation`
4. **Method:** GET or POST (both are supported).
5. **Schedule:** e.g. daily at 9:00 UTC → `0 9 * * *`, or every 6 hours → `0 */6 * * *`.
6. Save. The service will call your endpoint on the chosen schedule.

## Memory (512MB instances)

To avoid out-of-memory errors on free/low-memory plans, the handler processes at most **1 user per run** by default. Set in `.env`:

- `CRON_AUTOMATION_MAX_USERS_PER_RUN=1` (default; recommended for 512MB)
- Increase to 2–10 only if you have more RAM (e.g. paid plan).

If you schedule the cron frequently (e.g. every 6 hours), each run will process one user; over the day all users will still be covered.

## Response

The endpoint returns JSON, e.g.:

```json
{
  "users_processed": 1,
  "posts_created": 1,
  "errors": []
}
```

Errors list any users for whom the run failed (e.g. API/key issues).
