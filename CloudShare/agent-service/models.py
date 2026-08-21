from typing import Optional
from pydantic import BaseModel


class TransactionSignals(BaseModel):
    paymentIdCreated: bool
    bankResponseCode: Optional[str] = None
    otpAttempted: bool = False
    otpVerified: Optional[bool] = None
    signatureValid: bool = True
    secondsToFailure: int = 0


class DiagnoseRequest(BaseModel):
    orderId: str
    userName: Optional[str] = "there"
    amount: int
    currency: str = "INR"
    planId: str
    attemptCount: int = 0
    signals: TransactionSignals


class DiagnoseResponse(BaseModel):
    orderId: str
    diagnosedCause: str
    confidence: float
    reasoning: str
    recommendedAction: str  # RETRY | REMIND | REMIND_LATER | REQUEST_NEW_PAYMENT_METHOD | ESCALATE | STOP
    hinglishMessage: Optional[str] = None
