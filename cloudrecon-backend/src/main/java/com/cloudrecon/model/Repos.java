package com.cloudrecon.model;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public final class Repos {
    private Repos() {}

    public interface UserRepository extends JpaRepository<AppUser, Long> {
        Optional<AppUser> findByEmail(String email);
    }

    public interface JobRepository extends JpaRepository<Job, String> {
        List<Job> findByOwnerOrderByCreatedAtDesc(String owner);
        Optional<Job> findByIdAndOwner(String id, String owner);
    }
}
