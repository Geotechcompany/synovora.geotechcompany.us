# Cron: Auto-create posts from trends

Trigger the automation endpoint on a schedule so draft posts are created from trending topics for users who have automation enabled.

## Full endpoint URL

- **Base:** `https://synovora-geotechcompany-us.onrender.com`
- **Endpoint:** `/cron/run-automation`
- **Full URL (GET or POST):**  
  **`https://synovora-geotechcompany-us.onrender.com/cron/run-automation`**

Use this URL in [cron-job.org](https://cron-job.org), Render Cron, GitHub Actions, or system cron.

The endpoint **returns 202 Accepted immediately** and runs the automation in the background. This avoids **timeouts** on cron-job.org (and similar services) while trends, AI, and optional publish complete. You do not need to increase the request timeout.

## cron-job.org setup

1. Go to [cron-job.org](https://cron-job.org) and create or sign in to your account.
2. Create a new cron job.
3. **URL:** `https://synovora-geotechcompany-us.onrender.com/cron/run-automation`
4. **Method:** GET or POST (both are supported).
5. **Schedule:** e.g. daily at 9:00 UTC → `0 9 * * *`, or every 6 hours → `0 */6 * * *`.
6. Save. The service will call your endpoint on the chosen schedule.

## Image generation

Auto-created drafts include an image when **OPENAI_API_KEY** is set (DALL-E). To skip image generation on cron (e.g. to save memory or time), set:

- `CRON_AUTOMATION_SKIP_IMAGE=1`

## Auto-publish vs draft

Each user chooses in the **Automations** page (Dashboard → Automations → Automation settings):

- **Save as draft** – auto-created posts are saved as drafts for review.
- **Publish to LinkedIn automatically** – each auto-created post is published immediately (requires **LINKEDIN_TOKEN** and valid token).

Visibility for published posts can be set with **`CRON_AUTOMATION_PUBLISH_VISIBILITY=PUBLIC`** or **`CONNECTIONS`** (default **PUBLIC**). If publish fails (e.g. invalid token), the post remains as a draft; the cron run still succeeds.

## Memory (512MB instances)

To avoid out-of-memory errors on free/low-memory plans, the handler processes at most **1 user per run** by default. Set in `.env`:

- `CRON_AUTOMATION_MAX_USERS_PER_RUN=1` (default; recommended for 512MB)
- Increase to 2–10 only if you have more RAM (e.g. paid plan).

If image generation causes OOM, set `CRON_AUTOMATION_SKIP_IMAGE=1` so drafts are created without images. If you schedule the cron frequently (e.g. every 6 hours), each run will process one user; over the day all users will still be covered.

## How we avoid duplicate posts (same day / same week)

Each user has a **last run** timestamp (`last_auto_run_at`). When the cron runs:

- After it **successfully** creates a post for a user, it sets `last_auto_run_at` to that run’s time.
- Before running for a user again, it checks:
  - **Daily**: If the user already ran in the **last 23 hours**, the user is **skipped** (no second post that day).
  - **Weekly**: If the user already ran in the **last 7 days**, the user is **skipped** (no second post that week).

So “today’s post has been created and posted” is tracked by that timestamp: once we run for you and create (and optionally publish) a post, we won’t run for you again until the next day (daily) or next week (weekly), even if the cron is triggered multiple times.

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
