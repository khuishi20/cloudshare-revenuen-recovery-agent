package com.khushi.cloudshare.controller;

import com.khushi.cloudshare.Documents.PaymentTransactionDocument;
import com.khushi.cloudshare.Documents.ProfileDocument;
import com.khushi.cloudshare.repository.PaymentTransactionRepository;
import com.khushi.cloudshare.service.PaymentService;
import com.khushi.cloudshare.service.ProfileService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/transactions")
@RequiredArgsConstructor
public class TransactionController {
private final PaymentTransactionRepository paymentTransactionRepository;
private final ProfileService profileService;

@GetMapping
public ResponseEntity<?> getUsersTransaction(){
    ProfileDocument currentProfile=profileService.getCurrentProfile();
    String clerkId=currentProfile.getClerkId();
    List<PaymentTransactionDocument> transactionDocuments=paymentTransactionRepository.findByClerkIdAndStatusOrderByTransactionDateDesc(clerkId,"SUCCESS");
    return ResponseEntity.ok(transactionDocuments);
}

}

