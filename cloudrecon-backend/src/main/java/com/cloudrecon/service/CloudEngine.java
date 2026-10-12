package com.cloudrecon.service;

import org.springframework.beans.factory.annotation.Value;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

import javax.imageio.ImageIO;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.http.HttpClient;
import java.util.Base64;
import java.util.function.IntConsumer;

/**
 * Cloud detection and reconstruction.
 * Stage 2: detect bright, low-colour pixels (clouds) and widen the mask.
 * Stage 3: rebuild with the generative AI service if configured, otherwise a diffusion fill in pure Java.
 * Stage 4: compute quality metrics.
 */
@Service
public class CloudEngine {

    public record Result(BufferedImage output, BufferedImage mask, double coverage,
                         double cloudRemoval, double confidence, double score, String engine, String report) {}

    private final String aiUrl;

    public CloudEngine(@Value("${app.ai-service-url:}") String aiUrl) {
        this.aiUrl = aiUrl == null ? "" : aiUrl.trim();
    }

    public Result process(BufferedImage src, BufferedImage reference, String composite, String filename, IntConsumer stage) throws IOException {
        int w = src.getWidth(), h = src.getHeight();
        BufferedImage rgb = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = rgb.createGraphics();
        g.drawImage(src, 0, 0, null);
        g.dispose();

        stage.accept(2);
        boolean[] raw = detect(rgb, w, h);
        boolean[] cloud = dilate(raw, w, h, 4);
        long rawCount = count(raw), maskCount = count(cloud);
        BufferedImage mask = new BufferedImage(w, h, BufferedImage.TYPE_BYTE_GRAY);
        for (int i = 0; i < cloud.length; i++) mask.getRaster().setSample(i % w, i / w, 0, cloud[i] ? 255 : 0);

        stage.accept(3);
        // Preferred path: the Python AI service does detection, generative reconstruction and the report.
        if (!aiUrl.isEmpty()) {
            try {
                stage.accept(4);
                return remote(rgb, reference, composite, filename);
            } catch (Exception e) {
                System.err.println("AI service failed, using the Java fallback engine: " + e.getMessage());
            }
        }
        BufferedImage out = inpaint(rgb, cloud, w, h);
        String engine = "java-diffusion";

        stage.accept(4);
        long residual = count(detect(out, out.getWidth(), out.getHeight()));
        double coverage = 100.0 * maskCount / cloud.length;
        double removal = rawCount == 0 ? 100 : clamp(100.0 * (1 - (double) residual / rawCount));
        double confidence = clamp(100 - 0.4 * coverage);   // heuristic: less cloud = more known context
        double score = (removal + confidence) / 2;
        return new Result(out, mask, round(coverage), round(removal), round(confidence), round(score), engine, null);
    }

    private static double clamp(double v) { return Math.max(0, Math.min(100, v)); }
    private static double round(double v) { return Math.round(v * 10) / 10.0; }

    private static long count(boolean[] a) { long n = 0; for (boolean b : a) if (b) n++; return n; }

    private boolean[] detect(BufferedImage img, int w, int h) {
        int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        boolean[] m = new boolean[px.length];
        for (int i = 0; i < px.length; i++) {
            int r = (px[i] >> 16) & 255, g = (px[i] >> 8) & 255, b = px[i] & 255;
            int max = Math.max(r, Math.max(g, b)), min = Math.min(r, Math.min(g, b));
            m[i] = min >= 170 && (max - min) <= 45;
        }
        return m;
    }

    private boolean[] dilate(boolean[] m, int w, int h, int r) {
        boolean[] a = new boolean[m.length], b = new boolean[m.length];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                for (int k = Math.max(0, x - r); k <= Math.min(w - 1, x + r) && !a[y * w + x]; k++)
                    if (m[y * w + k]) a[y * w + x] = true;
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                for (int k = Math.max(0, y - r); k <= Math.min(h - 1, y + r) && !b[y * w + x]; k++)
                    if (a[k * w + x]) b[y * w + x] = true;
        return b;
    }

    /** Fills cloudy pixels from the outside in, averaging known neighbours on each pass. */
    private BufferedImage inpaint(BufferedImage img, boolean[] cloud, int w, int h) {
        int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        boolean[] known = new boolean[px.length];
        int remaining = 0;
        for (int i = 0; i < px.length; i++) { known[i] = !cloud[i]; if (cloud[i]) remaining++; }
        int[] idx = new int[Math.max(remaining, 1)], col = new int[idx.length];

        for (int pass = 0; remaining > 0 && pass < Math.max(w, h); pass++) {
            int n = 0;
            for (int y = 0; y < h; y++) {
                for (int x = 0; x < w; x++) {
                    int i = y * w + x;
                    if (known[i]) continue;
                    int r = 0, g = 0, b = 0, c = 0;
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            int nx = x + dx, ny = y + dy;
                            if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                            int j = ny * w + nx;
                            if (!known[j]) continue;
                            r += (px[j] >> 16) & 255; g += (px[j] >> 8) & 255; b += px[j] & 255; c++;
                        }
                    }
                    if (c > 0) { idx[n] = i; col[n++] = ((r / c) << 16) | ((g / c) << 8) | (b / c); }
                }
            }
            if (n == 0) break;
            for (int k = 0; k < n; k++) { px[idx[k]] = col[k]; known[idx[k]] = true; }
            remaining -= n;
        }
        BufferedImage out = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
        out.setRGB(0, 0, w, h, px, 0, w);
        return out;
    }

    private static ByteArrayResource named(BufferedImage img, String name) throws IOException {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        ImageIO.write(img, "png", b);
        return new ByteArrayResource(b.toByteArray()) {
            @Override public String getFilename() { return name; }
        };
    }

    private Result remote(BufferedImage rgb, BufferedImage reference, String composite, String filename) throws IOException {
        MultiValueMap<String, Object> parts = new LinkedMultiValueMap<>();
        parts.add("image", named(rgb, "image.png"));
        if (reference != null) parts.add("reference", named(reference, "reference.png"));
        parts.add("composite", composite);
        parts.add("filename", filename);
        // Force HTTP/1.1: the JDK client's HTTP/2 upgrade attempt confuses uvicorn.
        RestClient client = RestClient.builder()
                .requestFactory(new JdkClientHttpRequestFactory(HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build()))
                .build();
        JsonNode res = client.post()
                .uri(aiUrl + "/process")
                .contentType(MediaType.MULTIPART_FORM_DATA).body(parts)
                .retrieve().body(JsonNode.class);
        if (res == null) throw new IOException("AI service returned nothing");
        BufferedImage out = ImageIO.read(new ByteArrayInputStream(Base64.getDecoder().decode(res.get("output_png_b64").asText())));
        BufferedImage mask = ImageIO.read(new ByteArrayInputStream(Base64.getDecoder().decode(res.get("mask_png_b64").asText())));
        if (out == null || mask == null) throw new IOException("AI service returned an invalid image");
        return new Result(out, mask, res.get("coverage").asDouble(), res.get("cloudRemoval").asDouble(),
                res.get("confidence").asDouble(), res.get("score").asDouble(), res.get("engine").asText(),
                res.get("report").toString());
    }
}
