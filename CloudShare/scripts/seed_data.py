"""
Seeds ~45 synthetic FAILED/ERROR payment transactions into the CloudShare
`payment_transactions` collection.

Important design choice: we do NOT store the failure cause as a plain label.
Instead each doc gets realistic raw signals (bank response code, whether a
paymentId was ever generated, OTP attempt, HMAC signature validity, retry
count). The agent has to infer the cause from these signals, same as it
would from real Razorpay webhook data. We keep the ground-truth cause in a
separate field (`_trueCauseForEval`) purely so you can measure the agent's
diagnosis accuracy later - the agent service is never given this field.

Usage:
    pip install pymongo --break-system-packages
    python seed_data.py
"""

import random
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "cloudshare"

# Realistic-ish bank/NPCI decline code mapping used to derive signals.
CAUSE_WEIGHTS = {
    "INSUFFICIENT_FUNDS": 0.28,   # bank_response_code 51
    "CARD_EXPIRED": 0.16,         # bank_response_code 54
    "BANK_TIMEOUT": 0.20,         # bank_response_code 91/96
    "USER_ABANDONED": 0.24,       # no paymentId ever created
    "SIGNATURE_MISMATCH": 0.06,   # our own HMAC check failed
    "OTP_FAILED": 0.06,           # otp_attempted True, otp_verified False
}

BANK_CODE = {
    "INSUFFICIENT_FUNDS": "51",
    "CARD_EXPIRED": "54",
    "BANK_TIMEOUT": "91",
}

PLANS = {"BASIC": 499, "PREMIUM": 1499, "ULTIMATE": 2999}

FIRST_NAMES = ["Aarav", "Vivaan", "Ishaan", "Ananya", "Diya", "Sara", "Kabir",
               "Riya", "Aditya", "Meera", "Rohan", "Priya", "Karan", "Neha",
               "Arjun", "Tanya"]
LAST_NAMES = ["Sharma", "Verma", "Iyer", "Patel", "Gupta", "Nair", "Reddy",
              "Singh", "Mehta", "Das"]


def weighted_cause():
    causes, weights = zip(*CAUSE_WEIGHTS.items())
    return random.choices(causes, weights=weights, k=1)[0]


def derive_signals(cause: str):
    """Turn a ground-truth cause into the raw signals a real system would
    actually have, so the agent must infer the cause rather than read it."""
    signals = {
        "paymentIdCreated": True,
        "bankResponseCode": None,
        "otpAttempted": False,
        "otpVerified": None,
        "signatureValid": True,
        "secondsToFailure": random.randint(5, 90),
    }

    if cause == "USER_ABANDONED":
        signals["paymentIdCreated"] = False
        signals["secondsToFailure"] = random.randint(120, 900)  # sat idle
    elif cause == "SIGNATURE_MISMATCH":
        signals["signatureValid"] = False
    elif cause == "OTP_FAILED":
        signals["otpAttempted"] = True
        signals["otpVerified"] = False
    elif cause in BANK_CODE:
        signals["bankResponseCode"] = BANK_CODE[cause]

    return signals


def make_transaction(i: int, base_time: datetime):
    cause = weighted_cause()
    plan_id = random.choice(list(PLANS.keys()))
    amount = PLANS[plan_id]
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    clerk_id = f"user_{1000 + i}"
    tx_time = base_time - timedelta(
        days=random.randint(0, 10),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    status = "ERROR" if cause == "SIGNATURE_MISMATCH" else "FAILED"
    signals = derive_signals(cause)

    doc = {
        "clerkId": clerk_id,
        "orderId": f"order_seed_{i:04d}",
        "paymentId": f"pay_seed_{i:04d}" if signals["paymentIdCreated"] else None,
        "planId": plan_id,
        "amount": amount,
        "currency": "INR",
        "creditsAdded": 0,
        "status": status,
        "transactionDate": tx_time,
        "userEmail": f"{first.lower()}.{last.lower()}{i}@example.com",
        "userName": f"{first} {last}",
        "attemptCount": 0,
        "lastAttemptAt": None,
        # raw signals the agent will actually reason over
        "signals": signals,
        # ground truth, for your own accuracy measurement only
        "_trueCauseForEval": cause,
    }
    return doc


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["payment_transactions"]

    now = datetime.utcnow()
    docs = [make_transaction(i, now) for i in range(1, 46)]

    result = collection.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} synthetic failed transactions "
          f"into {DB_NAME}.payment_transactions")

    from collections import Counter
    counts = Counter(d["_trueCauseForEval"] for d in docs)
    for cause, n in counts.items():
        print(f"  {cause:20s} {n}")


if __name__ == "__main__":
    main()
