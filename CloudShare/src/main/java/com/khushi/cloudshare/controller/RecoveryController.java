package com.khushi.cloudshare.controller;

import com.khushi.cloudshare.Documents.PaymentTransactionDocument;
import com.khushi.cloudshare.Documents.RecoveryAuditLogDocument;
import com.khushi.cloudshare.repository.PaymentTransactionRepository;
import com.khushi.cloudshare.repository.RecoveryAuditLogRepository;
import com.khushi.cloudshare.service.RecoveryService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/recovery")
@RequiredArgsConstructor
public class RecoveryController {

    private final RecoveryService recoveryService;
    private final RecoveryAuditLogRepository recoveryAuditLogRepository;
    private final PaymentTransactionRepository paymentTransactionRepository;

    @PostMapping("/run-batch")
    public ResponseEntity<List<RecoveryAuditLogDocument>> runBatch() {
        return ResponseEntity.ok(recoveryService.runBatch());
    }

    @GetMapping("/audit")
    public ResponseEntity<List<RecoveryAuditLogDocument>> getAudit() {
        return ResponseEntity.ok(recoveryAuditLogRepository.findAllByOrderByDecidedAtDesc());
    }

    /**
     * Note: `recoveredAmount` reflects retry orders whose status has since
     * flipped to SUCCESS - in this demo build that happens via
     * scripts/simulate_settlement.py standing in for a real Razorpay
     * webhook. Swap that script for an actual webhook handler before this
     * number means anything outside the buildathon.
     */
    @GetMapping("/metrics")
    public ResponseEntity<Map<String, Object>> getMetrics() {
        List<RecoveryAuditLogDocument> auditLog = recoveryAuditLogRepository.findAll();
        List<PaymentTransactionDocument> retries = paymentTransactionRepository.findAll().stream()
                .filter(t -> t.getRetryOfOrderId() != null)
                .toList();

        long totalFailed = auditLog.stream().map(RecoveryAuditLogDocument::getOrderId).distinct().count();

        Map<String, Long> byOutcome = new HashMap<>();
        auditLog.forEach(a -> byOutcome.merge(a.getOutcome(), 1L, Long::sum));

        Map<String, Long> byCause = new HashMap<>();
        auditLog.forEach(a -> byCause.merge(a.getDiagnosedCause(), 1L, Long::sum));

        int attemptedAmount = retries.stream().mapToInt(PaymentTransactionDocument::getAmount).sum();
        int recoveredAmount = retries.stream()
                .filter(t -> "SUCCESS".equals(t.getStatus()))
                .mapToInt(PaymentTransactionDocument::getAmount)
                .sum();
        double recoveryRatePct = attemptedAmount == 0 ? 0.0 : (recoveredAmount * 100.0 / attemptedAmount);

        Map<String, Object> metrics = new HashMap<>();
        metrics.put("totalFailedTransactions", totalFailed);
        metrics.put("byOutcome", byOutcome);
        metrics.put("byDiagnosedCause", byCause);
        metrics.put("retryAttemptsCreated", retries.size());
        metrics.put("attemptedAmount", attemptedAmount);
        metrics.put("recoveredAmount", recoveredAmount);
        metrics.put("recoveryRatePct", Math.round(recoveryRatePct * 10) / 10.0);

        return ResponseEntity.ok(metrics);
    }
}

