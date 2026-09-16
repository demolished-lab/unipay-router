# Load Testing with Locust

The repository includes a Locust workload for the local UniPay Router simulator.
It exercises the health check, receiver setup, route listing, payment intents,
intent lookup, simulated confirmation, FX lookup, and a Razorpay-shaped webhook
fixture.

The workload never contacts a real payment provider and must only be used
against a local or explicitly authorized sandbox deployment.

## Install Locust

Install the optional load-test dependency:

```bash
pip install -e '.[loadtest]'
```

## Start the router

In terminal 1:

```bash
python -m unipay_router.server
```

## Run the interactive test

In terminal 2:

```bash
locust -f loadtest/locustfile.py --host http://127.0.0.1:3000
```

Open [http://localhost:8089](http://localhost:8089), enter a small number of
users and a gradual spawn rate, then start the test. Begin with 1–5 users to
validate behavior before increasing load.

## Run headless

For a repeatable local smoke benchmark:

```bash
locust -f loadtest/locustfile.py \
  --host http://127.0.0.1:3000 \
  --users 10 \
  --spawn-rate 2 \
  --run-time 60s \
  --headless \
  --csv=artifacts/locust
```

Create the output directory first:

```bash
mkdir -p artifacts
```

Locust writes request counts, failure counts, response-time percentiles, and
throughput to `artifacts/locust_*.csv`.

## Hosted testing

For a hosted sandbox, set the target explicitly:

```bash
locust -f loadtest/locustfile.py \
  --host https://your-sandbox.example.com \
  --users 25 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless
```

Do not point this workload at production or a real payment-provider callback
URL. Hosted free tiers may sleep, rate-limit, or suspend services under high
traffic. Load testing also consumes bandwidth and platform quotas.

## What to measure

Track the following Locust metrics:

| Metric | Why it matters |
|---|---|
| Median response time | Normal user experience |
| p95/p99 response time | Tail latency during contention |
| Requests per second | Sustained throughput |
| Failure rate | Correctness under load |
| `/v1/payment-intents` latency | Main routing path |
| Webhook latency | Provider callback responsiveness |
| Error distribution | Validation, authentication, or server failures |

The current MVP is in-memory and intentionally simple. Results are useful for
regression detection, not as a production capacity guarantee. Repeat benchmarks
with the same user count, spawn rate, duration, Python version, and host
conditions before comparing commits.

## Optional CI smoke check

Do not run a large Locust load test on every GitHub Actions job. For CI, use the
unit tests and a short one-user smoke run only when needed:

```bash
python -m unipay_router.server &
locust -f loadtest/locustfile.py --host http://127.0.0.1:3000 \
  --users 1 --spawn-rate 1 --run-time 5s --headless
```

The included GitHub Actions workflow validates the unit suite and repository
artifacts; full performance runs should be started manually against an
authorized environment.
