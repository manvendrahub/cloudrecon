package com.cloudrecon.service;

import com.cloudrecon.model.Job;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

/** Matches the frontend SatelliteJob type (status values: Completed, Processing, Queued, Failed). */
public record JobDto(String id, String code, String filename, String status, int stage,
                     double cloudCoverage, double cloudRemoval, double confidence, double reconstructionScore,
                     int width, int height, String engine, String date, String duration, String error,
                     String composite, String report) {

    private static final DateTimeFormatter FMT =
            DateTimeFormatter.ofPattern("dd MMM yyyy, HH:mm", Locale.ENGLISH).withZone(ZoneId.systemDefault());

    public static JobDto from(Job j) {
        String status = switch (j.status) {
            case COMPLETED -> "Completed";
            case PROCESSING -> "Processing";
            case FAILED -> "Failed";
            default -> "Queued";
        };
        return new JobDto(j.id, j.code, j.filename, status, j.stage, j.cloudCoverage, j.cloudRemoval,
                j.confidence, j.reconstructionScore, j.width, j.height, j.engine,
                FMT.format(j.createdAt), duration(j.durationMs, j.status), j.error, j.composite, j.report);
    }

    private static String duration(long ms, Job.Status s) {
        if (s == Job.Status.PROCESSING) return "Running";
        if (s == Job.Status.UPLOADED || s == Job.Status.QUEUED) return "Queued";
        long sec = ms / 1000;
        return sec < 60 ? String.format(Locale.ENGLISH, "%.1fs", ms / 1000.0) : (sec / 60) + "m " + String.format("%02d", sec % 60) + "s";
    }
}
