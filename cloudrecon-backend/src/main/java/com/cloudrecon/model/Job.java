package com.cloudrecon.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "jobs")
public class Job {
    public enum Status { UPLOADED, QUEUED, PROCESSING, COMPLETED, FAILED }

    @Id public String id;
    public String code;                 // e.g. CR-2026-0004
    public String owner;                // user email
    public String filename;
    @Enumerated(EnumType.STRING) public Status status = Status.UPLOADED;
    public int stage = 1;               // 1 validation, 2 detection, 3 reconstruction, 4 quality
    public int width, height;
    public double cloudCoverage;        // % of pixels masked
    public double cloudRemoval;         // % of detected cloud removed
    public double confidence;
    public double reconstructionScore;  // 0-100
    public String engine;
    public long durationMs;
    public Instant createdAt = Instant.now();
    @Column(length = 500) public String error;
    public String composite = "false-color";   // false-color (LISS-IV FCC) or natural
    @Lob public String report;                  // situation report as JSON

    protected Job() {}
    public Job(String id, String code, String owner, String filename) {
        this.id = id; this.code = code; this.owner = owner; this.filename = filename;
    }
}
