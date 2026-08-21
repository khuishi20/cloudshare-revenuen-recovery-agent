package com.khushi.cloudshare.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

// One file, two small DTOs - split into separate files if your team prefers that.

public class AgentDtos {

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    @Builder
    public static class DiagnoseRequestDto {
        private String orderId;
        private String userName;
        private int amount;
        private String currency;
        private String planId;
        private int attemptCount;
        private Map<String, Object> signals; // matches TransactionSignals shape in the Python service exactly
    }

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    public static class DiagnoseResponseDto {
        private String orderId;
        private String diagnosedCause;
        private double confidence;
        private String reasoning;
        private String recommendedAction;
        private String hinglishMessage;
    }
}

