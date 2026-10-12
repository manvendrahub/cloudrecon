"""CloudRecon AI service.

POST /process?composite=false-color|natural   (body: PNG bytes)
  -> JSON { output_png_b64, mask_png_b64, coverage, cloudRemoval, confidence, score, engine, report }

Reconstruction uses LaMa (a generative inpainting network) when `simple-lama-inpainting` is installed,
otherwise OpenCV Navier-Stokes inpainting. The cloud-free image is blended back into the original
only inside the cloud mask, so clear pixels are never changed.
"""
import base64
import io
import os
from datetime import datetime

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile
from PIL import Image

app = FastAPI(title="CloudRecon AI service")
MAX_SIDE = int(os.getenv("MAX_SIDE", "1024"))   # LaMa runs at most this many pixels on the long side

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image")
_gemini = _gtypes = None
if os.getenv("GEMINI_API_KEY"):
    try:
        from google import genai
        from google.genai import types as _gtypes
        _gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        print("Gemini enabled:", GEMINI_MODEL)
    except Exception as e:
        print("Gemini not available:", e)

_lama = None
ENGINE = "opencv-inpaint"
try:
    from simple_lama_inpainting import SimpleLama
    _lama = SimpleLama()
    ENGINE = "generative-ai"
    print("LaMa generative model loaded")
except Exception as e:  # missing package, no weights, no internet...
    print("LaMa not available, using OpenCV fallback:", e)


# ---------------------------------------------------------------- cloud detection
def detect(bgr: np.ndarray) -> np.ndarray:
    """Bright, low-colour pixels. Returns a boolean array."""
    b, g, r = (bgr[:, :, i].astype(np.int16) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    return (mn >= 150) & ((mx - mn) <= 60)


def dark_channel(bgr: np.ndarray):
    """Smoothed dark channel: high only where something veils the ground (cloud, haze). Rooftops stay low."""
    f = bgr.astype(np.float32)
    h, w = bgr.shape[:2]
    patch = max(15, int(min(h, w) * 0.06)) | 1
    dc = cv2.GaussianBlur(cv2.erode(f.min(axis=2), np.ones((patch, patch), np.uint8)), (0, 0), patch / 3)
    return dc, patch


def veil_level(img: np.ndarray, mask: np.ndarray) -> float:
    dc, _ = dark_channel(img)
    return float(dc[mask > 0].mean()) if (mask > 0).any() else 0.0


def cloud_mask(bgr: np.ndarray) -> np.ndarray:
    """Clouds = veiled areas (dark channel) + very white blobs + bright pixels next to those.
    Bright rooftops and roads, which are small and sit on a dark ground, are not clouds."""
    h, w = bgr.shape[:2]
    b, g, r = (bgr[:, :, i].astype(np.int16) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    dc, patch = dark_channel(bgr)
    chroma = cv2.GaussianBlur((mx - mn).astype(np.float32), (0, 0), patch / 3)       # cloud is colourless, sand and soil are not
    core = cv2.morphologyEx(((dc > 95) & (chroma <= 60)).astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    strong = ((mn >= 205) & ((mx - mn) <= 35)).astype(np.uint8) * 255
    strong = cv2.morphologyEx(strong, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    strong = cv2.morphologyEx(strong, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(strong, connectivity=8)
    keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= max(60, int(0.0004 * h * w))]
    strong = np.isin(labels, keep).astype(np.uint8) * 255

    weak = ((mn >= 150) & ((mx - mn) <= 60)).astype(np.uint8) * 255
    near = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (patch + 14, patch + 14)))
    m = cv2.bitwise_or(cv2.bitwise_or(core, strong), cv2.bitwise_and(weak, near))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    k = max(7, int(round(min(h, w) * 0.015))) | 1                          # widen to cover soft cloud edges
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    m[bgr.max(axis=2) < 10] = 0                                            # keep the black no-data border untouched
    return m


def dehaze_thin(bgr: np.ndarray, mask: np.ndarray):
    """Thin, see-through cloud: remove the veil and keep the ground that shows through.
    Returns (image, thick_mask). thick_mask = areas with no usable ground, still to be reconstructed."""
    if mask.max() == 0:
        return bgr.copy(), mask
    f = bgr.astype(np.float32)
    dc, patch = dark_channel(bgr)
    k = np.ones((patch, patch), np.uint8)
    A = np.maximum(f[dc >= np.percentile(dc, 99.5)].mean(axis=0), 1)        # colour of the cloud / haze
    dcn = cv2.GaussianBlur(cv2.erode((f / A).min(axis=2), k), (0, 0), patch / 3)
    t = np.clip(1 - 0.75 * dcn, 0.45, 1)                                    # transmission, gentle
    J = np.clip((f - A) / t[..., None] + A, 0, 255)
    inside = mask > 0
    thick = ((dcn > 0.8) | (f.min(axis=2) >= 185)) & inside              # opaque white = no ground visible
    thin = inside & (~thick)
    ring = (cv2.dilate(mask, np.ones((71, 71), np.uint8)) > 0) & (~inside)
    if ring.sum() > 500 and thin.sum() > 0:                                 # repaired area gets the surroundings' colour statistics
        for c in range(3):
            a_, b_ = J[:, :, c][thin], f[:, :, c][ring]
            J[:, :, c] = np.clip(J[:, :, c] - a_.mean() + b_.mean(), 0, 255)   # shift brightness only, keep the detail
    alpha = cv2.GaussianBlur(thin.astype(np.uint8) * 255, (0, 0), 8).astype(np.float32)[..., None] / 255
    alpha = alpha * (cv2.dilate(mask, np.ones((5, 5), np.uint8)) > 0)[..., None]   # never touch clear pixels
    out = np.clip(f * (1 - alpha) + J * alpha, 0, 255).astype(np.uint8)
    thick_mask = cv2.dilate(thick.astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
    return out, thick_mask


def match_colors(img: np.ndarray, target: np.ndarray, clear: np.ndarray) -> np.ndarray:
    """Match brightness and contrast of `img` to `target` using pixels that are clear in both."""
    out = img.astype(np.float32)
    if clear.sum() > 500:
        for c in range(3):
            a, b = out[:, :, c][clear], target[:, :, c][clear].astype(np.float32)
            out[:, :, c] = (out[:, :, c] - a.mean()) / (a.std() + 1e-6) * b.std() + b.mean()
    return np.clip(out, 0, 255).astype(np.uint8)


def gemini_fill(bgr: np.ndarray, mask: np.ndarray):
    """Ask Gemini to remove clouds. Returns an image at the original size, or None."""
    h, w = mask.shape
    scale = min(1.0, 1024 / max(h, w))
    small = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1 else bgr
    prompt = ("This is a satellite image with clouds. Remove all clouds and reconstruct the ground underneath "
              "(land, water, vegetation, roads) so it looks like a clear-sky satellite image. Keep the framing, "
              "scale, colours and every cloud-free area exactly the same. Do not add text, borders or new objects. "
              "Return only the edited image.")
    resp = _gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))],
        config=_gtypes.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )
    for part in resp.candidates[0].content.parts:
        data = getattr(getattr(part, "inline_data", None), "data", None)
        if data:
            g = cv2.cvtColor(np.array(Image.open(io.BytesIO(data)).convert("RGB")), cv2.COLOR_RGB2BGR)
            return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
    return None


def reconstruct(bgr: np.ndarray, mask: np.ndarray):
    """Returns (image, engine_name). Order: Gemini (if configured), LaMa, OpenCV."""
    h, w = mask.shape
    if mask.max() == 0:
        return bgr.copy(), ENGINE
    filled, used = None, None
    if _gemini is not None:
        try:
            g = gemini_fill(bgr, mask)
            if g is not None:
                filled, used = match_colors(g, bgr, mask == 0), "gemini"
        except Exception as e:
            print("Gemini failed, falling back:", e)
    if filled is None and _lama is not None:
        scale = min(1.0, MAX_SIDE / max(h, w))
        sw, sh = max(8, int(w * scale)), max(8, int(h * scale))
        small = cv2.resize(bgr, (sw, sh), interpolation=cv2.INTER_AREA) if scale < 1 else bgr
        smask = cv2.resize(mask, (sw, sh), interpolation=cv2.INTER_NEAREST) if scale < 1 else mask
        res = _lama(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)), Image.fromarray(smask).convert("L"))
        filled = cv2.cvtColor(np.array(res), cv2.COLOR_RGB2BGR)
        if filled.shape[:2] != (h, w):
            filled = cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)
        used = "generative-ai"
    if filled is None:
        filled, used = cv2.inpaint(bgr, mask, 7, cv2.INPAINT_NS), "opencv-inpaint"
    alpha = cv2.GaussianBlur(mask, (0, 0), sigmaX=3).astype(np.float32)[:, :, None] / 255.0
    return np.clip(bgr * (1 - alpha) + filled * alpha, 0, 255).astype(np.uint8), used


# ---------------------------------------------------------------- scene analysis + report
def land_cover(bgr: np.ndarray, composite: str) -> dict:
    R, G, B = (bgr[:, :, 2].astype(np.float32), bgr[:, :, 1].astype(np.float32), bgr[:, :, 0].astype(np.float32))
    bright = (R + G + B) / 3
    if composite == "false-color":      # LISS-IV FCC: red = NIR, green = Red band, blue = Green band
        ndvi = (R - G) / (R + G + 1e-6)
        veg = ndvi > 0.15
        water = (~veg) & (R < 60)
    else:                               # natural colour
        veg = (G > R + 8) & (G > B + 4)
        water = (~veg) & (bright < 95) & (B >= R - 5)
    bare = ~(veg | water)
    pct = lambda a: round(float(a.mean()) * 100, 1)
    return {"vegetation": pct(veg), "water": pct(water), "bareBuilt": pct(bare)}


def build_report(filename, composite, coverage, cloud_removal, confidence, lc, shape, engine, ref_share=None):
    if coverage < 10:
        quality = "Good"
    elif coverage < 40:
        quality = "Moderate"
    else:
        quality = "Low: much of the scene is estimated"
    if ref_share is not None and ref_share >= 0.8:
        quality = "Good: filled from a real reference image"
    obs = [f"{coverage}% of the scene was cloud covered and has been reconstructed; {cloud_removal}% of detected cloud was removed."]
    if ref_share is not None:
        obs.append(f"{round(ref_share * 100)}% of the reconstructed area was filled from the cloud-free reference image, so it shows real observations, not model guesses. These areas show the ground as it was on the reference date, so changes between the two dates (river course, sediment, crops, tide) are not reflected there.")
    if lc["vegetation"] >= 40:
        obs.append(f"Vegetation dominates the scene ({lc['vegetation']}%), which suggests cropland, forest or grassland.")
    elif lc["vegetation"] >= 10:
        obs.append(f"Vegetation covers {lc['vegetation']}% of the scene, mixed with other land cover.")
    else:
        obs.append(f"Vegetation is sparse ({lc['vegetation']}%).")
    if lc["water"] >= 25:
        obs.append(f"Water or very dark surface covers {lc['water']}% of the scene. Compare with an earlier date to check for flooding, waterlogging or reservoir change. Shadows and wet soil can be classed as water.")
    elif lc["water"] >= 3:
        obs.append(f"Water or dark surface covers {lc['water']}% of the scene (rivers, tanks or shadows).")
    if lc["bareBuilt"] >= 50:
        obs.append(f"Bare soil, fallow land or built-up area dominates ({lc['bareBuilt']}%).")
    recs = []
    if ref_share is None and coverage >= 15:
        recs.append("For accurate results, upload a cloud-free image of the same area from another date as a reference. A single image cannot show what is under thick cloud.")
    if coverage >= 40:
        recs.append("Cloud cover is high. Acquire another pass or a cloud-free date for decisions that need accuracy.")
    if lc["water"] >= 25:
        recs.append("Cross-check water extent with SAR data or a previous LISS-IV scene before reporting a flood.")
    recs.append("Treat reconstructed areas as estimates. Validate against ground truth or a cloud-free scene before operational use.")
    return {
        "title": f"Situation report: {filename}",
        "generatedAt": datetime.now().strftime("%d %b %Y, %H:%M"),
        "summary": (f"{filename} ({shape[1]}x{shape[0]} px, {'false-colour' if composite == 'false-color' else 'natural-colour'}). "
                    f"{coverage}% was obscured by cloud and rebuilt. After reconstruction the scene is about "
                    f"{lc['vegetation']}% vegetation, {lc['water']}% water or dark surface and {lc['bareBuilt']}% bare soil or built-up land."),
        "quality": {"label": quality, "cloudCoverage": coverage, "confidence": confidence, "engine": engine},
        "landCover": {**lc, "cloud": coverage},
        "observations": obs,
        "recommendations": recs,
        "limitations": [
            "Land cover is a simple colour and index classification, not a trained classifier.",
            "Reconstructed pixels are model estimates, not measurements.",
            "A single image cannot show change over time. Use two dates to detect change.",
        ],
    }


def b64png(arr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", arr)
    return base64.b64encode(buf.tobytes()).decode()


@app.get("/health")
def health():
    return {"status": "ok", "engine": ENGINE, "gemini": _gemini is not None}


def valid_bbox(img):
    """Bounding box (y0, y1, x0, x1) of the non-black part of an image."""
    ys, xs = np.where(img.max(axis=2) >= 10)
    if len(ys) == 0:
        return 0, img.shape[0], 0, img.shape[1]
    return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1


def refine_shift(bgr, ref, mask):
    """Remove a small leftover offset between the two images (phase correlation on clear pixels)."""
    h, w = mask.shape
    ok = (mask == 0) & (bgr.max(axis=2) >= 10) & (ref.max(axis=2) >= 10)
    if ok.sum() < 5000:
        return ref
    g1 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g2 = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g1[~ok], g2[~ok] = g1[ok].mean(), g2[ok].mean()
    (dx, dy), resp = cv2.phaseCorrelate(g1, g2, cv2.createHanningWindow((w, h), cv2.CV_32F))
    if resp < 0.05 or max(abs(dx), abs(dy)) < 0.5 or abs(dx) > 0.1 * w or abs(dy) > 0.1 * h:
        return ref
    return cv2.warpAffine(ref, np.float32([[1, 0, -dx], [0, 1, -dy]]), (w, h), flags=cv2.INTER_LINEAR, borderValue=0)


def fill_from_reference(bgr, ref, mask):
    """Fill cloudy pixels from a cloud-free image of the same area (another date).
    Returns (image, leftover_mask, share_filled_from_reference, updated_cloud_mask)."""
    h, w = mask.shape
    # 1. Align: fit the valid (non-black) area of the reference onto the valid area of the main image
    y0, y1, x0, x1 = valid_bbox(bgr)
    ry0, ry1, rx0, rx1 = valid_bbox(ref)
    canvas = np.zeros_like(bgr)
    canvas[y0:y1, x0:x1] = cv2.resize(ref[ry0:ry1, rx0:rx1], (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    ref = refine_shift(bgr, canvas, mask)
    ref_nodata = cv2.dilate((ref.max(axis=2) < 10).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ref_clouds = (cloud_mask(ref) > 0) | ref_nodata          # reference pixels we must not copy

    # 2. Match brightness and contrast to the main image
    clear = (mask == 0) & (~ref_clouds)
    diff = np.abs(bgr.astype(np.float32).mean(axis=2) - ref.astype(np.float32).mean(axis=2))
    if clear.sum() > 500:                                       # ignore real changes between dates when matching colours
        clear = clear & (diff <= np.percentile(diff[clear], 80))
    adj = ref.astype(np.float32)
    if clear.sum() > 500:
        for c in range(3):
            a, b = adj[:, :, c][clear], bgr[:, :, c][clear].astype(np.float32)
            adj[:, :, c] = (adj[:, :, c] - a.mean()) / (a.std() + 1e-6) * b.std() + b.mean()
    adj = np.clip(adj, 0, 255)

    # 3. Thin haze the brightness rule missed: greyish pixels much brighter than the reference
    f = bgr.astype(np.float32)
    bright, chroma = f.mean(axis=2), f.max(axis=2) - f.min(axis=2)
    ring = max(15, int(min(h, w) * 0.05)) | 1                 # only the halo around detected cloud, not distant land
    near = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ring, ring))) > 0
    haze = ((bright - adj.mean(axis=2)) > 35) & (bright > 140) & (chroma <= 50) & near & (~ref_clouds) & (bgr.max(axis=2) >= 10)
    haze = cv2.morphologyEx(haze.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    haze = cv2.dilate(haze, np.ones((5, 5), np.uint8))
    haze[bgr.max(axis=2) < 10] = 0
    mask = cv2.bitwise_or(mask, haze)

    # 4. Copy reference pixels into the (updated) cloud mask with soft edges
    usable = ((mask > 0) & (~ref_clouds)).astype(np.uint8) * 255
    share = float((usable > 0).sum()) / max(1, int((mask > 0).sum()))
    alpha = cv2.GaussianBlur(usable, (0, 0), sigmaX=3).astype(np.float32) / 255.0
    alpha = (alpha * (cv2.dilate(mask, np.ones((3, 3), np.uint8)) > 0))[:, :, None]   # never touch clear pixels
    out = np.clip(bgr * (1 - alpha) + adj * alpha, 0, 255).astype(np.uint8)
    leftover = ((mask > 0) & ref_clouds).astype(np.uint8) * 255
    return out, leftover, share, mask


def run_pipeline(bgr, ref, composite, filename):
    mask = cloud_mask(bgr)
    share, thick_share = None, 1.0
    if ref is not None:
        out, leftover, share, mask = fill_from_reference(bgr, ref, mask)
        if leftover.max() > 0:
            out, _ = reconstruct(out, leftover)
        engine = "reference-fill"
    else:
        out, thick = dehaze_thin(bgr, mask)                    # thin cloud: remove the veil
        if thick.max() > 0:                                    # thick cloud: reconstruct
            out, used = reconstruct(out, thick)
            engine = "dehaze+" + used
            thick_share = float((thick > 0).sum()) / max(1, int((mask > 0).sum()))
        else:
            engine, thick_share = "dehaze", 0.0

    coverage = round(float((mask > 0).mean()) * 100, 1)
    before, after = veil_level(bgr, mask), veil_level(out, mask)
    removal = 100.0 if before <= 0 else round(max(0.0, min(100.0, 100 * (1 - after / before))), 1)
    if share is not None:
        confidence = 100 - 0.4 * coverage * (1 - share) - 0.05 * coverage * share
    else:
        confidence = 100 - 0.4 * coverage * min(1.0, thick_share) - 0.1 * coverage * (1 - min(1.0, thick_share))
        if thick_share > 0 and not engine.endswith(("generative-ai", "gemini")):
            confidence -= 10
    confidence = round(max(0.0, min(100.0, confidence)), 1)
    score = round((removal + confidence) / 2, 1)
    report = build_report(filename, composite, coverage, removal, confidence, land_cover(out, composite), bgr.shape, engine, share)
    return out, mask, coverage, removal, confidence, score, engine, report


@app.post("/process")
async def process(image: UploadFile = File(...), reference: UploadFile | None = File(None),
                  composite: str = Form("false-color"), filename: str = Form("image")):
    bgr = cv2.imdecode(np.frombuffer(await image.read(), np.uint8), cv2.IMREAD_COLOR)
    ref = None
    if reference is not None:
        data = await reference.read()
        if data:
            ref = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    out, mask, coverage, removal, confidence, score, engine, report = run_pipeline(bgr, ref, composite, filename)
    return {"output_png_b64": b64png(out), "mask_png_b64": b64png(mask), "coverage": coverage,
            "cloudRemoval": removal, "confidence": confidence, "score": score, "engine": engine, "report": report}
