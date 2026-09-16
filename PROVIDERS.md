# Payment Gateway Configuration

## What “zero cost” means here

UniPay Router has two separate modes:

1. **Local simulator:** completely free, requires no gateway account, and is
   the default mode in this repository. It calculates routes using local
   provider profiles and does not move money.
2. **Gateway sandbox/test mode:** free for simulated transactions in the
   provider’s test environment. It requires a provider account and test
   credentials, but it does not charge or settle real payments.

There is no universal zero-cost path for **live** payment processing. Live
payments may incur transaction fees, GST/taxes, onboarding/KYC requirements,
settlement rules, and provider-specific eligibility conditions. Never put live
credentials in this repository or commit them to Git.

## Recommended local-first workflow

You can develop the whole router without a gateway account:

```bash
# Terminal 1: start UniPay Router
python -m unipay_router.server

# Terminal 2: register a receiver
curl -X POST http://localhost:3000/v1/receiver-preferences \
  -H 'Content-Type: application/json' \
  -d '{"receiver_id":"bob","handle":"bob@unipay","preferred_methods":["upi"]}'

# Create a route-only intent; this does not contact a gateway
curl -X POST http://localhost:3000/v1/payment-intents \
  -H 'Content-Type: application/json' \
  -d '{"amount":1000,"currency":"INR","receiver_handle":"bob@unipay","sender":{"preferred_methods":["upi"]}}'
```

For UI integration tests, call `POST /v1/payment-intents/{id}/confirm`. The
response includes `"simulated": true`; it does not contact a bank or provider.

## Gateway comparison

| Gateway | Free test mode | Test credentials | Test webhooks | Live processing |
|---|---|---|---|---|
| Razorpay | Yes, after signup; Test Mode uses no real money | Test `key_id` and `key_secret` | Requires a public URL; validate `X-Razorpay-Signature` | Fees and eligibility apply |
| Cashfree Payments | Yes; Test environment uses simulated operations | Test `x-client-id` and `x-client-secret` | Requires a public endpoint; verify the signed raw payload | Fees, GST, KYC, and offer restrictions apply |
| PayU India | Yes; test key and salt are generated after registration | Test merchant `key` and `Salt-32 bit` | Requires public HTTPS, HTTP 200, and fast responses | Fees and GST apply |

The exact provider documentation links are listed in each section below.

## 1. Razorpay Test Mode

### Create free test credentials

1. Create an account at the [Razorpay signup page](https://accounts.razorpay.com/auth/?auth_intent=signup).
2. Open the [Razorpay Dashboard](https://dashboard.razorpay.com/) and switch to
   **Test Mode**.
3. Go to **Account & Settings → Website and app settings → API Keys → Generate
   Key**. Razorpay documents that a website is not required to generate Test
   Mode keys.
4. Store the generated test `key_id` and `key_secret` outside Git. Test and
   Live modes use separate credential sets.

Official references: [Test and Live modes](https://razorpay.com/docs/payments/dashboard/test-live-modes), [API key setup](https://razorpay.com/docs/payments/dashboard/account-settings/api-keys), and [sandbox setup](https://razorpay.com/docs/api/sandbox-setup).

### Test instruments

- UPI success: `success@razorpay`
- UPI failure: `failure@razorpay`
- Domestic Visa: `4100 2800 0000 1007`
- Domestic Mastercard: `5555 5100 0008 1006`
- Domestic RuPay: `6527 6589 0000 1005`
- Test cards use a random CVV and any future expiry.
- Razorpay’s [test card reference](https://razorpay.com/docs/payments/payments/test-card-details)
  contains international cards and additional decline/error scenarios.

Test Checkout is a mock payment page. Test API keys do not deduct real money.
UPI Intent and QR flows are Live Mode flows, so do not treat them as free local
simulation capabilities.

### Webhooks

Use the local receiver endpoint:

```text
POST /v1/webhooks/razorpay
```

Razorpay cannot deliver webhooks to `localhost` directly. Use a public HTTPS
endpoint or a suitable tunnel during development. Razorpay documents port 80
or 443 requirements and warns that several local/testing domains are blocked.

For a real Razorpay adapter:

- Validate `X-Razorpay-Signature` with the webhook secret and the **raw request
  body** using HMAC-SHA256.
- Use `x-razorpay-event-id` for idempotency because duplicate delivery is
  possible.
- Configure separate Test and Live webhook URLs.

References: [Razorpay webhooks](https://razorpay.com/docs/webhooks) and [webhook validation](https://razorpay.com/docs/webhooks/validate-test).

### Live-cost warning

Razorpay Test Mode is free simulation. Live processing is not universally free;
Razorpay publishes standard pricing and may offer limited promotions with
eligibility, caps, taxes, and expiry conditions. Check the current [Razorpay
pricing page](https://razorpay.com/pricing/) before activating Live Mode.

## 2. Cashfree Payments Test Environment

### Create free test credentials

1. Create an account at the [Cashfree merchant signup page](https://merchant.cashfree.com/merchants/signup?source-action=Home%20page&action=Sign%20Up&button-id=StartNow_Navbar).
2. Log in to the [Merchant Dashboard](https://merchant.cashfree.com/merchant/).
3. Switch to **Test** using the top-right environment control.
4. Open **Payment Gateway Dashboard → Developers → API Keys**. Cashfree
   auto-generates Payment Gateway test keys.
5. Use the test credentials only with the sandbox endpoint
   `https://sandbox.cashfree.com`.

Cashfree Payment Gateway credentials are separate from Payouts credentials.
The current authentication headers are:

```text
x-client-id: <test client ID>
x-client-secret: <test client secret>
```

Official references: [quick start](https://www.cashfree.com/docs/payments/quickstart-guide), [authentication](https://www.cashfree.com/docs/api-reference/authentication), and [test data](https://www.cashfree.com/docs/api-reference/payments/data-to-test-integration).

### Test instruments

- Card Visa: `4706131211212123`
- Card Mastercard: `5105105105105100`
- Card RuPay: `6074825972083818`
- Universal test card OTP: `111000`
- Test card expiry: `03/2028`
- Test card CVV: `123`
- Test UPI success: `testsuccess@gocash`
- Test UPI failure: `testfailure@gocash`
- Invalid UPI VPA: `testinvalid@gocash`
- Test net banking: bank `TEST Bank`, payment code `3333`, bank API code `TESTR`

The official test-data page includes timeout, decline, risk, insufficient-funds,
and other simulated outcomes. Sandbox limitations include no PayPal or
bank-transfer testing and only a generic test wallet rather than individual
wallet providers.

### Webhooks

Use the local receiver endpoint:

```text
POST /v1/webhooks/cashfree
```

Cashfree cannot reach a localhost-only server. Use a public HTTPS endpoint or a
provider-appropriate development tunnel. For a real Cashfree adapter:

- Verify `x-webhook-signature` using `x-webhook-timestamp`, the raw request
  payload, and the Payment Gateway Secret Key.
- Return HTTP 200 after successful processing.
- Handle duplicate delivery and validate the documented idempotency header for
  webhook versions that require it.

References: [webhook overview](https://www.cashfree.com/docs/payments/online/webhooks/overview) and [webhook documentation](https://www.cashfree.com/docs/payments/webhooks).

### Live-cost warning

Cashfree’s test environment is simulated and has no financial impact. Live
pricing, GST, KYC, and eligibility rules apply separately. Cashfree may offer
limited 0%-fee promotions for eligible merchants, but these have dates, GMV
caps, exclusions, taxes, and withdrawal/change conditions. Check the current
[Cashfree pricing FAQ](https://www.cashfree.com/docs/help/account/pricing) and
[charges page](https://www.cashfree.com/payment-gateway-charges/).

## 3. PayU India Test Mode

### Create free test credentials

1. Register at [PayU merchant onboarding](https://onboarding.payu.in/app/account).
2. Sign in to the [PayU Merchant Dashboard](https://onboarding.payu.in/app/account/signin).
3. Switch the dashboard to **Test Mode**.
4. Open **Developer → API Keys**. PayU documents that test credentials are
   generated automatically after registration, before production onboarding is
   complete.
5. Use the test hosted-checkout endpoint:

```text
https://test.payu.in/_payment
```

The test credentials are:

```text
key: <test merchant key>
salt: <test Salt-32 bit>
```

Generate payment hashes server-side with SHA-512. Never expose the salt in
browser code or commit it to Git.

Official references: [test integration](https://docs.payu.in/docs/test-integration), [test key and salt](https://docs.payu.in/docs/generate-test-merchant-key-and-salt), and [test account registration](https://docs.payu.in/docs/register-for-a-merchant-account-on-dashboard).

### Test instruments

- Mastercard: `5123456789012346`, expiry `05/30`, CVV `123`, OTP `123456`
- Visa: `4012001037141112`, expiry `05/30`, CVV `123`, OTP `123456`
- RuPay: `6082015309577308`, expiry `05/30`, CVV `123`, OTP `123456`
- Test UPI: `anything@payu` and `9999999999@payu.in`
- Net banking: username `payu`, password `payu`, OTP `123456`

PayU documents additional wallet and card scenarios in its [test card, UPI,
and wallet reference](https://docs.payu.in/docs/test-cards-upi-id-and-wallets).
The documented UPI Intent and UPI in-app flows are not available in PayU Test
Mode.

### Webhooks and callbacks

Use the local receiver endpoint:

```text
POST /v1/webhooks/payu
```

PayU requires a publicly accessible HTTPS endpoint rather than localhost. Its
documentation specifies HTTPS/443, HTTP 200 responses, and a response within
five seconds. Hosted checkout also requires publicly reachable HTTPS `surl` and
`furl` URLs; these are separate from the dashboard webhook endpoint.

References: [webhook alerts](https://docs.payu.in/docs/webhook-alerts) and [webhook events](https://docs.payu.in/docs/webhook-events-and-sample-payloads).

### Live-cost warning

PayU Test Mode simulates payments and does not settle funds. PayU’s live pricing
page lists transaction charges and GST; it also says pricing can change and
custom pricing may apply. Check the current [PayU pricing page](https://payu.in/pricing/)
before enabling production access.

## Secret management

Do not put gateway secrets in `config/hyperswitch.toml`, source files, Docker
images, Git commits, screenshots, or chat messages. For local experiments, use
environment variables in an untracked `.env` file or export them in your shell:

```bash
export RAZORPAY_KEY_ID='rzp_test_...'
export RAZORPAY_KEY_SECRET='...'
export CASHFREE_CLIENT_ID='TEST_...'
export CASHFREE_CLIENT_SECRET='...'
export PAYU_MERCHANT_KEY='...'
export PAYU_MERCHANT_SALT='...'
```

The current zero-cost UniPay MVP does not consume these variables yet; it uses
local deterministic provider profiles. They are documented for the next
provider-adapter phase. Add them only when implementing and testing a real
sandbox adapter.

## Adding a real adapter

Before adding a provider adapter:

1. Confirm the provider’s current sandbox API and authentication documentation.
2. Keep the adapter behind an explicit test/live environment switch.
3. Add request signing, timeout handling, retries, idempotency, and structured
   provider error mapping.
4. Verify webhook signatures against the raw body and deduplicate events.
5. Add sandbox integration tests using only test credentials and instruments.
6. Keep the local simulator available so ordinary development remains free.

The router’s current webhook endpoints accept normalized provider payloads for
local development, but they are not a substitute for provider-specific
signature verification and production reconciliation.
