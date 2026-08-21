package com.parth.cloudshare.Documents;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
@NoArgsConstructor
@Builder
@Document(collection = "recovery_audit_log")
public class RecoveryAuditLogDocument {
    private String id;
    private String orderId;
    private String clerkId;
    private int amount;
    private String currency;

    // what the agent decided, and why - this is the explainability trail
    private String diagnosedCause;
    private double confidence;
    private String reasoning;
    private String recommendedAction; // RETRY | REMIND | REMIND_LATER | REQUEST_NEW_PAYMENT_METHOD | ESCALATE | STOP
    private String hinglishMessage;

    // what actually happened when we executed that decision
    private String outcome; // RETRY_INITIATED | MESSAGE_QUEUED | ESCALATED | EXHAUSTED
    private String newOrderId; // set only when outcome == RETRY_INITIATED

    private int attemptNumber;
    private LocalDateTime decidedAt;
}
