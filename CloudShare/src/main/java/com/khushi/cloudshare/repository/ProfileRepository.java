package com.khushi.cloudshare.repository;

import com.khushi.cloudshare.Documents.ProfileDocument;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface ProfileRepository extends MongoRepository<ProfileDocument, String> {
    Optional<ProfileDocument> findByEmail(String email);
    ProfileDocument findByClerkId(String clerkId);
    Boolean existsByClerkId(String clerkId);
}

