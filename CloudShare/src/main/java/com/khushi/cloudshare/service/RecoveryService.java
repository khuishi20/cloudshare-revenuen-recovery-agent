package com.khushi.cloudshare.service;

import com.khushi.cloudshare.Documents.PaymentTransactionDocument;
import com.khushi.cloudshare.Documents.RecoveryAuditLogDocument;
import com.khushi.cloudshare.dto.AgentDtos.DiagnoseRequestDto;
import com.khushi.cloudshare.dto.AgentDtos.DiagnoseResponseDto;
import com.khushi.cloudshare.repository.PaymentTransactionRepository;
import com.khushi.cloudshare.repository.RecoveryAuditLogRepository;
import com.razorpay.Order;
import com.razorpay.RazorpayClient;
import lombok.RequiredArgsConstructor;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class RecoveryService {

    private static final int MAX_RETRIES = 3;

    private final PaymentTransactionRepository paymentTransactionRepository;
    private final RecoveryAuditLogRepository recoveryAuditLogRepository;
    private final RestTemplate restTemplate;

    @Value("${razorpay.key.id}")
    private String razorpayKeyId;
    @Value("${razorpay.key.secret}")
    private String razorpaySecret;
    @Value("${agent.service.url}")
    private String agentServiceUrl;

    /**
     * Runs the recovery loop over every FAILED/ERROR transaction that hasn't
     * already been resolved or exhausted. Every decision is logged to the
     * audit trail regardless of what action is taken - that's the point.
     */
    public List<RecoveryAuditLogDocument> runBatch() {
        List<PaymentTransactionDocument> candidates = paymentTransactionRepository.findAll().stream()
                .filter(t -> "FAILED".equals(t.getStatus()) || "ERROR".equals(t.getStatus()))
                .filter(t -> t.getAttemptCount() < MAX_RETRIES)
                .toList();

        return candidates.stream().map(this::processOne).toList();
    }

    private RecoveryAuditLogDocument processOne(PaymentTransactionDocument tx) {
        DiagnoseRequestDto request = DiagnoseRequestDto.builder()
                .orderId(tx.getOrderId())
                .userName(tx.getUserName())
                .amount(tx.getAmount())
                .currency(tx.getCurrency())
                .planId(tx.getPlanId())
                .attemptCount(tx.getAttemptCount())
                .signals(tx.getSignals())
                .build();

        DiagnoseResponseDto diagnosis = restTemplate.postForObject(
                agentServiceUrl + "/diagnose", request, DiagnoseResponseDto.class);

        String outcome;
        String newOrderId = null;

        switch (diagnosis.getRecommendedAction()) {
            case "RETRY" -> {
                newOrderId = createRetryOrder(tx, diagnosis.getDiagnosedCause());
                outcome = "RETRY_INITIATED";
            }
            case "REMIND", "REMIND_LATER", "REQUEST_NEW_PAYMENT_METHOD" -> {
                // Message is logged, not actually sent, in this demo build.
                // Wire this to an SMS/WhatsApp provider before using it for real.
                outcome = "MESSAGE_QUEUED";
            }
            case "ESCALATE" -> outcome = "ESCALATED";
            default -> outcome = "EXHAUSTED"; // STOP
        }

        tx.setAttemptCount(tx.getAttemptCount() + 1);
        tx.setLastAttemptAt(LocalDateTime.now());
        tx.setDiagnosedCause(diagnosis.getDiagnosedCause());
        paymentTransactionRepository.save(tx);

        RecoveryAuditLogDocument logEntry = RecoveryAuditLogDocument.builder()
                .orderId(tx.getOrderId())
                .clerkId(tx.getClerkId())
                .amount(tx.getAmount())
                .currency(tx.getCurrency())
                .diagnosedCause(diagnosis.getDiagnosedCause())
                .confidence(diagnosis.getConfidence())
                .reasoning(diagnosis.getReasoning())
                .recommendedAction(diagnosis.getRecommendedAction())
                .hinglishMessage(diagnosis.getHinglishMessage())
                .outcome(outcome)
                .newOrderId(newOrderId)
                .attemptNumber(tx.getAttemptCount())
                .decidedAt(LocalDateTime.now())
                .build();

        return recoveryAuditLogRepository.save(logEntry);
    }

    /** Creates a fresh Razorpay order for a retry attempt, linked back to the original failure. */
    private String createRetryOrder(PaymentTransactionDocument original, String diagnosedCause) {
        try {
            RazorpayClient razorpayClient = new RazorpayClient(razorpayKeyId, razorpaySecret);
            JSONObject orderRequest = new JSONObject();
            orderRequest.put("amount", original.getAmount());
            orderRequest.put("currency", original.getCurrency());
            orderRequest.put("receipt", "retry_" + System.currentTimeMillis());
            Order order = razorpayClient.orders.create(orderRequest);
            String newOrderId = order.get("id");

            PaymentTransactionDocument retryTx = PaymentTransactionDocument.builder()
                    .clerkId(original.getClerkId())
                    .orderId(newOrderId)
                    .planId(original.getPlanId())
                    .amount(original.getAmount())
                    .currency(original.getCurrency())
                    .status("PENDING")
                    .transactionDate(LocalDateTime.now())
                    .userEmail(original.getUserEmail())
                    .userName(original.getUserName())
                    .attemptCount(0)
                    .diagnosedCause(diagnosedCause)
                    .retryOfOrderId(original.getOrderId())
                    .build();
            paymentTransactionRepository.save(retryTx);
            return newOrderId;
        } catch (Exception e) {
            // A failed retry-order creation is itself worth knowing about,
            // but shouldn't crash the whole batch.
            return null;
        }
    }
}

