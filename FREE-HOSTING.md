# Free Hosting Quickstart

This guide deploys the current UniPay Router MVP for demos, API experiments,
and sandbox webhook testing. It does not make the router a production payment
processor. The current application stores receiver preferences and payment
intents in memory, so restarts and serverless cold starts can clear state.

## Which free option should you choose?

| Platform | Best for | Important limitations |
|---|---|---|
| **Render Free Web Service** | Running the existing threaded HTTP server with the fewest changes | Sleeps after 15 minutes without inbound traffic, cold starts take about a minute, local files are ephemeral |
| **Vercel Python Function** | Small stateless API demos and frontend-adjacent deployments | Serverless execution, in-memory state is not durable, the normal long-running server is not used |

For this repository, **Render is the recommended first deployment** because it
runs the normal `python -m unipay_router.server` process and exposes the
`/health` endpoint directly. Vercel support is included through the WSGI
adapter in `vercel_app.py`.

Render’s current free-plan documentation states that free web services can
spin down after 15 minutes without inbound traffic, take about one minute to
start again, and lose local filesystem changes on restarts/redeploys. Vercel’s
Python runtime loads a WSGI/ASGI entrypoint as a Function rather than running a
permanent process. Review the current platform terms before relying on either
for external provider webhooks.

## Option A: Render Free Web Service

### 1. Confirm the repository is pushed

Use the public repository:

```text
https://github.com/demolished-lab/unipay-router
```

### 2. Create the service

1. Open the [Render Dashboard](https://dashboard.render.com/).
2. Select **New → Web Service**.
3. Connect GitHub and select `demolished-lab/unipay-router`.
4. Choose branch `main`.
5. Set the following values:

| Render field | Value |
|---|---|
| Runtime | Python |
| Build Command | `pip install -e .` |
| Start Command | `python -m unipay_router.server` |
| Plan | **Free** |
| Health Check Path | `/health` |

6. Add environment variables:

```text
HOST=0.0.0.0
PORT=10000
UNIPAY_API_KEY=<generate-your-own-long-random-value>
```

`PORT=10000` matches Render’s documented default. The server already reads
`PORT` and binds to `HOST`.

7. Click **Create Web Service** and wait for the first deploy to finish.

The service receives an HTTPS URL similar to:

```text
https://unipay-router-xxxx.onrender.com
```

### 3. Verify the deployment

```bash
export BASE_URL='https://unipay-router-xxxx.onrender.com'
export API_KEY='your-value'

curl -i "$BASE_URL/health" \
  -H "X-API-Key: $API_KEY"
```

A successful response has HTTP `200` and JSON containing `"status":"ok"`.
The first request after idle may take longer because the free service is waking
up.

### 4. Import the Postman collection

Import [the Postman collection](postman/UniPay-Router.postman_collection.json),
then set:

```text
base_url = https://unipay-router-xxxx.onrender.com
api_key  = the same UNIPAY_API_KEY value
```

Run the requests in this order:

1. Health check
2. Create or update receiver
3. Resolve receiver handle
4. Create payment intent
5. Get payment intent
6. Confirm payment intent (simulation)
7. Routes and FX requests
8. Webhook fixtures

### 5. Configure sandbox webhooks

Use the Render HTTPS URL directly:

```text
Razorpay: https://unipay-router-xxxx.onrender.com/v1/webhooks/razorpay
Cashfree: https://unipay-router-xxxx.onrender.com/v1/webhooks/cashfree
PayU:     https://unipay-router-xxxx.onrender.com/v1/webhooks/payu
```

Add the relevant sandbox webhook secret as a Render environment variable:

```text
RAZORPAY_WEBHOOK_SECRET=...
CASHFREE_WEBHOOK_SECRET=...
```

Do not use Live Mode credentials for this deployment. Review the provider
signature requirements in `PROVIDERS.md` before accepting callbacks.

### 6. Free-plan cautions

- Free services sleep after inactivity and can delay the first webhook.
- The process may restart at any time.
- In-memory receivers and payment intents disappear on restart.
- The local filesystem is not durable; do not use it as a database.
- Free Render Postgres is not a durable zero-cost production solution; the
  current Render documentation says free databases expire after 30 days.
- Monitor monthly included usage and outbound traffic in the Render Dashboard.

## Option B: Vercel Python Function

Vercel cannot run the repository’s long-lived threaded server as a normal
process. This repository includes `vercel_app.py`, a WSGI adapter that exposes
the same API through a Python Function.

### 1. Install and authenticate the Vercel CLI

```bash
npm install --global vercel
vercel login
```

Alternatively, import the GitHub repository from the Vercel Dashboard.

### 2. Deploy from the repository root

```bash
cd unipay-router
vercel
```

Accept the detected project settings. For a production deployment:

```bash
vercel --prod
```

The repository includes:

- `vercel_app.py` with the WSGI `app` entrypoint
- `vercel.json` with the Python version, rewrite, and bundle exclusions
- `[tool.vercel] entrypoint = "vercel_app:app"` in `pyproject.toml`

### 3. Add environment variables

In the Vercel project settings, add:

```text
UNIPAY_API_KEY=<generate-your-own-long-random-value>
RAZORPAY_WEBHOOK_SECRET=<sandbox-secret-if-used>
CASHFREE_WEBHOOK_SECRET=<sandbox-secret-if-used>
```

Or configure them with the CLI using Vercel’s secret workflow. Never put the
values in `vercel.json` or Git.

### 4. Verify the Function

```bash
export BASE_URL='https://your-project.vercel.app'
export API_KEY='your-value'

curl -i "$BASE_URL/health" \
  -H "X-API-Key: $API_KEY"
```

The rewrite sends requests to `vercel_app.py`, which translates WSGI requests
to the existing `UniPayAPI` implementation.

### 5. Configure sandbox webhooks

Use the Vercel HTTPS URL:

```text
Razorpay: https://your-project.vercel.app/v1/webhooks/razorpay
Cashfree: https://your-project.vercel.app/v1/webhooks/cashfree
PayU:     https://your-project.vercel.app/v1/webhooks/payu
```

### 6. Vercel limitations for this MVP

- Function instances are not a durable process or database.
- In-memory receiver and payment state may differ between invocations.
- Do not depend on process-local state for real payments or reconciliation.
- Provider webhook retries and idempotency must be implemented before
  production use.
- Keep the function bundle small and avoid long-running work.

## Security checklist for either platform

- Set a strong `UNIPAY_API_KEY`; do not leave authentication blank on a public
  deployment.
- Use sandbox gateway credentials and test webhooks only.
- Store secrets in platform environment variables, never in source control.
- Keep provider webhook signature verification enabled.
- Do not send card numbers, CVVs, or payment secrets to this application.
- Treat the deployment as a demo/sandbox environment until durable storage,
  idempotency, reconciliation, monitoring, and compliance controls are added.

## Official platform references

- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Render web services](https://render.com/docs/web-services)
- [Render free plan](https://render.com/docs/free)
