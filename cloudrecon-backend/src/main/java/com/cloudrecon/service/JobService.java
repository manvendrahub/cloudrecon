package com.cloudrecon.service;

import com.cloudrecon.model.Job;
import com.cloudrecon.model.Repos.JobRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Year;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Service
public class JobService {
    public static final Set<String> KINDS = Set.of("input", "mask", "output");

    private final JobRepository jobs;
    private final CloudEngine engine;
    private final Path dir;
    private final ExecutorService pool = Executors.newFixedThreadPool(2);

    public JobService(JobRepository jobs, CloudEngine engine, @Value("${app.storage-dir}") String storageDir) throws IOException {
        this.jobs = jobs;
        this.engine = engine;
        this.dir = Path.of(storageDir);
        Files.createDirectories(dir);
    }

    public Job upload(MultipartFile file, String owner, String composite, MultipartFile reference) throws IOException {
        BufferedImage img = ImageIO.read(file.getInputStream());
        if (img == null) {
            throw new IllegalArgumentException("Unsupported file. Upload an 8-bit TIFF, PNG or JPEG image.");
        }
        String id = UUID.randomUUID().toString();
        String code = "CR-%d-%04d".formatted(Year.now().getValue(), jobs.count() + 1);
        String name = file.getOriginalFilename() == null ? "image" : file.getOriginalFilename();
        Job job = new Job(id, code, owner, name);
        job.composite = "natural".equals(composite) ? "natural" : "false-color";
        job.width = img.getWidth();
        job.height = img.getHeight();
        ImageIO.write(img, "png", path(id, "input").toFile());
        if (reference != null && !reference.isEmpty()) {
            BufferedImage ref = ImageIO.read(reference.getInputStream());
            if (ref == null) throw new IllegalArgumentException("Unsupported reference image. Use PNG, JPG or 8-bit TIFF.");
            ImageIO.write(ref, "png", path(id, "reference").toFile());
        }
        return jobs.save(job);
    }

    public Job start(String id, String owner) throws IOException {
        Job job = owned(id, owner);
        if (job.status == Job.Status.PROCESSING || job.status == Job.Status.QUEUED) return job;
        job.status = Job.Status.QUEUED;
        job.stage = 1;
        job.error = null;
        jobs.save(job);
        BufferedImage img = ImageIO.read(path(id, "input").toFile());
        Path rp = path(id, "reference");
        BufferedImage ref = Files.exists(rp) ? ImageIO.read(rp.toFile()) : null;
        pool.submit(() -> run(id, img, ref));
        return job;
    }

    private void run(String id, BufferedImage img, BufferedImage ref) {
        long t0 = System.currentTimeMillis();
        Job job = jobs.findById(id).orElseThrow();
        try {
            job.status = Job.Status.PROCESSING;
            jobs.save(job);
            CloudEngine.Result r = engine.process(img, ref, job.composite, job.filename, stage -> { job.stage = stage; jobs.save(job); });
            ImageIO.write(r.output(), "png", path(id, "output").toFile());
            ImageIO.write(r.mask(), "png", path(id, "mask").toFile());
            job.cloudCoverage = r.coverage();
            job.cloudRemoval = r.cloudRemoval();
            job.confidence = r.confidence();
            job.reconstructionScore = r.score();
            job.engine = r.engine();
            job.report = r.report();
            job.status = Job.Status.COMPLETED;
        } catch (Throwable e) {
            job.status = Job.Status.FAILED;
            job.error = String.valueOf(e.getMessage());
        } finally {
            job.durationMs = System.currentTimeMillis() - t0;
            jobs.save(job);
        }
    }

    public Job owned(String id, String owner) {
        return jobs.findByIdAndOwner(id, owner)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));
    }

    public List<Job> history(String owner) { return jobs.findByOwnerOrderByCreatedAtDesc(owner); }

    public Path imagePath(String id, String owner, String kind) {
        owned(id, owner);
        Path p = path(id, kind);
        if (!KINDS.contains(kind) || !Files.exists(p)) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Image not available");
        return p;
    }

    private Path path(String id, String kind) { return dir.resolve(id + "_" + kind + ".png"); }
}
