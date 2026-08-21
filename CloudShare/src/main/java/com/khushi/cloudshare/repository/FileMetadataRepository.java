package com.khushi.cloudshare.repository;

import com.khushi.cloudshare.Documents.FileMetadataDocument;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface FileMetadataRepository extends MongoRepository<FileMetadataDocument, String> {
    List<FileMetadataDocument> findByClerkId(String clerkId);
    Long countByClerkId(String clerkId);
}

