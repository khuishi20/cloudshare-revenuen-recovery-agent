# CloudShare Revenue Recovery Agent — build kit

Everything here plugs into your existing CloudShare repo for the Razorpay
AI Buildathon (Revenue Recovery track). Nothing here needs your existing
code to change shape — it's additive.

## What's in this folder

```
agent-service/        Python FastAPI microservice — the "agent brain"
  main.py               /diagnose and /diagnose-batch endpoints
  diagnosis.py           rule-based diagnosis + Hinglish message generation
  models.py               request/response schemas
  requirements.txt

java-additions/        Drop into your Spring Boot project
  01_PaymentTransactionDocument_ADDITIONS.md   fields to add to your existing document
  RecoveryAuditLogDocument.java                new Mongo collection: every decision, logged
  RecoveryAuditLogRepository.java
  RecoveryService.java                          calls the agent, executes the bounded action
  RecoveryController.java                       /recovery/run-batch, /audit, /metrics
  RestTemplateConfig.java                       bean needed by RecoveryService
  AgentDtos.java                                 request/response shape for the agent call

scripts/
  seed_data.py            generates 45 synthetic failed transactions with realistic signals
  simulate_settlement.py  simulates the bank actually resolving retry attempts
  evaluate_accuracy.py    measures diagnosis accuracy against ground truth

dashboard/
  RecoveryDashboard.jsx   React component — metrics + audit trail, ledger/stamp styling
```

## How the pieces connect

```
payment_transactions (Mongo, your existing collection)
        │  FAILED / ERROR rows with realistic signals
        ▼
RecoveryService.runBatch()  ──POST /diagnose──▶  FastAPI agent service
        │  (Spring Boot)                          (rule-based diagnosis +
        │                                          Hinglish message)
        │  executes bounded action:
        │   RETRY → new Razorpay order, status PENDING
        │   REMIND* → message logged (not actually sent in this demo)
        │   ESCALATE / STOP → logged only
        ▼
recovery_audit_log (Mongo, new collection)
        │
        ▼
GET /recovery/metrics + /recovery/audit  ──▶  RecoveryDashboard.jsx
```

## Setup, in order

**1. Seed the failure data**
```bash
pip install pymongo --break-system-packages
python scripts/seed_data.py
```

**2. Run the agent service** (already tested and working)
```bash
cd agent-service
pip install -r requirements.txt --break-system-packages
uvicorn main:app --port 8123
```
Optional: `export ANTHROPIC_API_KEY=...` before starting if you want the
Hinglish messages lightly LLM-polished. Works fine without it — falls back
to the templates, which is actually the safer choice for a live demo where
you don't want a network call breaking mid-pitch.

Sanity check:
```bash
python scripts/evaluate_accuracy.py
```

**3. Wire up Spring Boot**
- Add the fields from `java-additions/01_PaymentTransactionDocument_ADDITIONS.md`
  to your existing `PaymentTransactionDocument.java`
- Copy the other `.java` files into the matching packages (`Documents`,
  `repository`, `service`, `controller`, `config`)
- Add to `application.properties`:
  ```
  agent.service.url=http://127.0.0.1:8123
  ```
- **Before you rebuild**: move `razorpay.key.id`, `razorpay.key.secret`,
  and `clerk.webhook.secret` out of `application.properties` and into
  environment variables — you're about to make this repo public.
- Run the app, then trigger a batch:
  ```
  POST http://localhost:8080/api/v1/recovery/run-batch
  ```

**4. Simulate settlement, then check the real numbers**
```bash
python scripts/simulate_settlement.py
```
Then hit `GET /api/v1/recovery/metrics` — that's your real, non-cherry-picked
recovery rate.

**5. Dashboard**
Drop `dashboard/RecoveryDashboard.jsx` into your React app. It fetches from
`/api/v1/recovery/metrics` and `/audit` automatically, and falls back to
demo data if the backend isn't reachable yet — so you can preview the UI
before the Java side is wired up.

## Being honest about scope (worth saying in your pitch)

- Diagnosis is rule-based over structured signals, not a raw LLM call
  reasoning over free text — that's a deliberate choice for
  explainability (the track explicitly asks for "every money action
  explainable"), and it gets 100% accuracy on the seeded signals because
  each cause maps cleanly to a signal pattern. Real production data would
  be noisier; say that in the pitch rather than let it go unstated.
- The LLM only touches the *message wording*, never the money decision.
- Settlement is simulated (`simulate_settlement.py`), standing in for a
  real Razorpay webhook — call this out plainly rather than imply it's
  live production data.
- Message sending is logged, not actually dispatched via SMS/WhatsApp —
  fine to say "logged, ready to wire to a real channel" in the demo.
