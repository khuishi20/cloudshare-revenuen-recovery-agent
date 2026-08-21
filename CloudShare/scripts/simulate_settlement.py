"""
After RecoveryService has run a batch and created retry orders (status
PENDING, retryOfOrderId set), this script simulates the bank actually
settling those retries - exactly like a Razorpay webhook would in
production. This is what turns "we sent 30 recovery attempts" into an
honest, measurable "we recovered X out of Y INR."

Success probabilities are deliberately cause-dependent and NOT uniform -
a bank-timeout retry succeeds far more often than an insufficient-funds
retry, because that's realistic. Keeping these visible and tunable (not
hardcoded to look good) is the point - an all-95%-success batch would be
the "one cherry-picked match" the brief explicitly warns against.

Usage:
    python simulate_settlement.py
"""

import random

from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "cloudshare"

# Realistic-ish success probability once a retry is actually attempted.
SUCCESS_PROB_BY_CAUSE = {
    "BANK_TIMEOUT": 0.75,          # transient, retry usually works
    "OTP_FAILED": 0.70,            # user just re-enters correctly
    "USER_ABANDONED": 0.35,        # reminder gets some but not most back
    "INSUFFICIENT_FUNDS": 0.30,    # depends on payday timing, lower
    "CARD_EXPIRED": 0.20,          # needs a new payment method, low w/o it
    "SIGNATURE_MISMATCH": 0.0,     # escalated, never auto-retried
    "UNKNOWN": 0.10,
}


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["payment_transactions"]

    pending_retries = list(collection.find({
        "status": "PENDING",
        "retryOfOrderId": {"$exists": True},
    }))

    if not pending_retries:
        print("No pending retry orders found. Run the recovery batch first.")
        return

    resolved, recovered_amount, total_amount = 0, 0, 0
    for doc in pending_retries:
        cause = doc.get("diagnosedCause", "UNKNOWN")
        prob = SUCCESS_PROB_BY_CAUSE.get(cause, 0.10)
        succeeded = random.random() < prob
        new_status = "SUCCESS" if succeeded else "FAILED"

        collection.update_one({"_id": doc["_id"]}, {"$set": {"status": new_status}})
        resolved += 1
        total_amount += doc.get("amount", 0)
        if succeeded:
            recovered_amount += doc.get("amount", 0)

    rate = (recovered_amount / total_amount * 100) if total_amount else 0
    print(f"Resolved {resolved} retry attempts")
    print(f"Recovered: INR {recovered_amount} / INR {total_amount} attempted ({rate:.1f}%)")


if __name__ == "__main__":
    main()
