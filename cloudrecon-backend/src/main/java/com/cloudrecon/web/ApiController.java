package com.cloudrecon.web;

import com.cloudrecon.model.Job;
import com.cloudrecon.service.JobDto;
import com.cloudrecon.service.JobService;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.TextStyle;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@RestController
@RequestMapping("/api")
public class ApiController {
    public record StartRequest(String imageId) {}
    public record Activity(String day, long images) {}
    public record Stats(long imagesProcessed, long completed, double avgCloudCoverage,
                        double avgReconstruction, JobDto latest, List<Activity> activity) {}

    private final JobService jobs;

    public ApiController(JobService jobs) { this.jobs = jobs; }

    @PostMapping("/images/upload")
    public JobDto upload(@RequestParam("file") MultipartFile file,
                         @RequestParam(value = "composite", defaultValue = "false-color") String composite,
                         @RequestParam(value = "reference", required = false) MultipartFile reference,
                         Authentication auth) throws IOException {
        return JobDto.from(jobs.upload(file, auth.getName(), composite, reference));
    }

    @PostMapping("/analysis/start")
    public JobDto start(@RequestBody StartRequest r, Authentication auth) throws IOException {
        return JobDto.from(jobs.start(r.imageId(), auth.getName()));
    }

    @GetMapping("/analysis/{id}")
    public JobDto analysis(@PathVariable String id, Authentication auth) {
        return JobDto.from(jobs.owned(id, auth.getName()));
    }

    @GetMapping("/results/{id}")
    public JobDto result(@PathVariable String id, Authentication auth) {
        return JobDto.from(jobs.owned(id, auth.getName()));
    }

    @GetMapping("/results/{id}/{kind}")
    public ResponseEntity<Resource> image(@PathVariable String id, @PathVariable String kind, Authentication auth) {
        return ResponseEntity.ok().contentType(MediaType.IMAGE_PNG)
                .body(new FileSystemResource(jobs.imagePath(id, auth.getName(), kind)));
    }

    @GetMapping("/results/{id}/download")
    public ResponseEntity<Resource> download(@PathVariable String id, Authentication auth) {
        Job j = jobs.owned(id, auth.getName());
        String base = j.filename.replaceAll("\\.[^.]+$", "");
        return ResponseEntity.ok().contentType(MediaType.IMAGE_PNG)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename(base + "_reconstructed.png").build().toString())
                .body(new FileSystemResource(jobs.imagePath(id, auth.getName(), "output")));
    }

    @GetMapping("/history")
    public List<JobDto> history(Authentication auth) {
        return jobs.history(auth.getName()).stream().map(JobDto::from).toList();
    }

    @GetMapping("/dashboard/stats")
    public Stats stats(Authentication auth) {
        List<Job> all = jobs.history(auth.getName());
        List<Job> done = all.stream().filter(j -> j.status == Job.Status.COMPLETED).toList();
        double cloud = done.stream().mapToDouble(j -> j.cloudCoverage).average().orElse(0);
        double score = done.stream().mapToDouble(j -> j.reconstructionScore).average().orElse(0);

        LocalDate today = LocalDate.now();
        ZoneId zone = ZoneId.systemDefault();
        List<Activity> activity = new ArrayList<>();
        for (int i = 6; i >= 0; i--) {
            LocalDate d = today.minusDays(i);
            long n = all.stream().filter(j -> j.createdAt.atZone(zone).toLocalDate().equals(d)).count();
            DayOfWeek dow = d.getDayOfWeek();
            activity.add(new Activity(dow.getDisplayName(TextStyle.SHORT, Locale.ENGLISH), n));
        }
        JobDto latest = done.isEmpty() ? null : JobDto.from(done.get(0));
        return new Stats(all.size(), done.size(), Math.round(cloud * 10) / 10.0, Math.round(score * 10) / 10.0, latest, activity);
    }
}
