"""
Calls the running agent service for every seeded transaction and compares
its diagnosedCause against the ground-truth `_trueCauseForEval` field
(which the agent is never shown). Prints overall accuracy plus a
per-cause confusion breakdown - this is the number you quote in the pitch
video and put in the README, not a cherry-picked example.

Usage (agent service must be running on :8123):
    python evaluate_accuracy.py
"""

from collections import Counter

import requests
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "cloudshare"
AGENT_URL = "http://127.0.0.1:8123/diagnose"


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    docs = list(db["payment_transactions"].find({"_trueCauseForEval": {"$exists": True}}))

    if not docs:
        print("No seeded evaluation transactions found. Run seed_data.py first.")
        return

    correct = 0
    confusion = Counter()

    for doc in docs:
        payload = {
            "orderId": doc["orderId"],
            "userName": doc.get("userName", "there"),
            "amount": doc["amount"],
            "currency": doc.get("currency", "INR"),
            "planId": doc["planId"],
            "attemptCount": doc.get("attemptCount", 0),
            "signals": doc["signals"],
        }
        resp = requests.post(AGENT_URL, json=payload, timeout=10)
        resp.raise_for_status()
        diagnosed = resp.json()["diagnosedCause"]
        truth = doc["_trueCauseForEval"]

        confusion[(truth, diagnosed)] += 1
        if diagnosed == truth:
            correct += 1

    total = len(docs)
    print(f"Diagnosis accuracy: {correct}/{total} ({correct/total*100:.1f}%)\n")

    print("Confusion (true -> diagnosed):")
    for (truth, diagnosed), n in sorted(confusion.items()):
        marker = "" if truth == diagnosed else "  <-- misdiagnosed"
        print(f"  {truth:20s} -> {diagnosed:20s}  x{n}{marker}")


if __name__ == "__main__":
    main()
