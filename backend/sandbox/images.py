"""Runner images: the /api/health report and the background thread that keeps them pulled."""
import sys, time

from sandbox import lsp, runner

IMG_STATE = {}   # image -> ready | pulling | missing


def health():
    try:
        runner.api("GET", "/version", timeout=5); ok, err = True, None
    except runner.DockerError as e: ok, err = False, str(e)
    return {"ok": True, "docker": ok, "error": err,
            "images": {lang: IMG_STATE.get(img, "missing") for lang, img in runner.IMAGES.items() if lang != "cpp"},
            "assist": {lang: IMG_STATE.get(img, "missing") for lang, img in runner.LSP_IMAGES.items()}}


def image_keeper():
    """Sweep leftover runners, then pull any missing runner image. Retries while Docker is unreachable."""
    swept = False
    while True:
        try:
            if not swept: runner.sweep(); lsp.sweep(); swept = True
            for img in dict.fromkeys([*runner.IMAGES.values(), *runner.LSP_IMAGES.values()]):
                if IMG_STATE.get(img) == "ready": continue
                if runner.image_ready(img): IMG_STATE[img] = "ready"; continue
                if img.startswith("ilab-"): IMG_STATE[img] = "missing"; continue   # built by compose / install.sh
                IMG_STATE[img] = "pulling"; runner.pull(img)
                IMG_STATE[img] = "ready" if runner.image_ready(img) else "missing"
        except Exception as e:  # never let the keeper thread die
            print("image keeper:", e, file=sys.stderr)
            for img, st in IMG_STATE.items():
                if st == "pulling": IMG_STATE[img] = "missing"
        time.sleep(30 if all(v == "ready" for v in IMG_STATE.values()) and IMG_STATE else 10)
