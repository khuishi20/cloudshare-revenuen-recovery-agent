package com.parth.cloudshare.repository;

import com.parth.cloudshare.Documents.RecoveryAuditLogDocument;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface RecoveryAuditLogRepository extends MongoRepository<RecoveryAuditLogDocument, String> {
    List<RecoveryAuditLogDocument> findAllByOrderByDecidedAtDesc();
}
