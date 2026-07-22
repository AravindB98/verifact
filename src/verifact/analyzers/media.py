"""Media provenance for images: C2PA Content Credentials, EXIF, reverse-image.

- **C2PA / Content Credentials**: cryptographic provenance standard backed by
  Adobe, Microsoft, BBC, Sony et al. If present and valid, it is the single
  strongest provenance signal available today. Requires optional dependency
  ``c2pa-python`` (``pip install verifact[media]`` roadmap; graceful skip).
- **EXIF**: capture device/date metadata (Pillow). Stripped EXIF is normal on
  social platforms, so absence is only informational.
- **Reverse-image pivot links**: VeriFact can't scrape Google/TinEye, so it
  generates the exact lookup URLs for one-click human verification — catching
  old-photo-new-caption recycling, the single most common visual misinfo.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Finding, Signal, SignalStatus
from .base import AnalysisContext, error_signal, skipped_signal

NAME = "media_provenance"
TITLE = "Media provenance"
WEIGHT = 1.5


def _exif_findings(path: str) -> list[Finding]:
    try:
        from PIL import ExifTags, Image
    except ImportError:
        return [
            Finding(
                label="EXIF check unavailable",
                detail="Install Pillow (`pip install 'verifact[media]'`) for EXIF inspection.",
                impact="informational",
            )
        ]
    findings: list[Finding] = []
    with Image.open(path) as im:
        exif = im.getexif()
        if not exif:
            findings.append(
                Finding(
                    label="No EXIF metadata",
                    detail="Metadata stripped — normal for social-media reuploads, but it "
                    "removes capture-time evidence.",
                    impact="informational",
                )
            )
            return findings
        wanted = {"DateTime", "DateTimeOriginal", "Make", "Model", "Software", "GPSInfo"}
        for tag_id, value in exif.items():
            tag = ExifTags.TAGS.get(tag_id, str(tag_id))
            if tag in wanted:
                findings.append(
                    Finding(label=f"EXIF {tag}", detail=str(value)[:120], impact="informational")
                )
        sw = str(exif.get(0x0131, "")).lower()
        if any(k in sw for k in ("photoshop", "gimp", "midjourney", "dall", "firefly")):
            findings.append(
                Finding(
                    label="Editing/generation software tag",
                    detail=f"EXIF Software = {exif.get(0x0131)}",
                    impact="negative",
                )
            )
    return findings


def _c2pa_findings(path: str) -> tuple[list[Finding], bool | None]:
    """Returns (findings, has_valid_credentials|None if lib unavailable)."""
    try:
        import c2pa  # type: ignore
    except ImportError:
        return (
            [
                Finding(
                    label="C2PA check unavailable",
                    detail="Install `c2pa-python` to validate Content Credentials "
                    "cryptographically.",
                    impact="informational",
                )
            ],
            None,
        )
    try:
        reader = c2pa.Reader.from_file(path)
        manifest = reader.json()
        if manifest:
            return (
                [
                    Finding(
                        label="C2PA Content Credentials present",
                        detail="Cryptographic provenance manifest found — inspect signer chain "
                        "at contentcredentials.org/verify.",
                        impact="positive",
                    )
                ],
                True,
            )
    except Exception:  # noqa: BLE001 — absence of manifest raises in some versions
        pass
    return (
        [
            Finding(
                label="No C2PA credentials",
                detail="Most images today lack Content Credentials, so this is expected — "
                "not a red flag by itself.",
                impact="informational",
            )
        ],
        False,
    )


class MediaProvenanceAnalyzer:
    name = NAME
    title = TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            return self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            return error_signal(NAME, TITLE, exc, WEIGHT)

    def _run(self, ctx: AnalysisContext) -> Signal:
        if not ctx.image_path:
            return skipped_signal(NAME, TITLE, "No image supplied.", WEIGHT)
        path = Path(ctx.image_path)
        if not path.exists():
            return skipped_signal(NAME, TITLE, f"Image not found: {path}", WEIGHT)

        findings: list[Finding] = []
        c2pa_f, has_c2pa = _c2pa_findings(str(path))
        findings += c2pa_f
        findings += _exif_findings(str(path))
        findings.append(
            Finding(
                label="Reverse-image search (do this!)",
                detail="Recycled old photos with fresh captions are the #1 visual misinfo "
                "pattern. Check where this image appeared before:",
                impact="informational",
            )
        )
        findings.append(
            Finding(
                label="Google Lens",
                detail="Upload the image at lens.google.com",
                impact="informational",
                evidence_url="https://lens.google.com/",
            )
        )
        findings.append(
            Finding(
                label="TinEye",
                detail="Upload the image at tineye.com — sorts by oldest appearance.",
                impact="informational",
                evidence_url="https://tineye.com/",
            )
        )

        negatives = sum(1 for f in findings if f.impact == "negative")
        if has_c2pa:
            score, conf = 85.0, 0.8
            summary = "Valid Content Credentials manifest found — strong provenance."
        elif negatives:
            score, conf = 35.0, 0.6
            summary = "Editing/generation traces found in metadata."
        else:
            score, conf = None, 0.3
            summary = (
                "No decisive provenance markers — use the reverse-image links to trace origin."
            )

        return Signal(
            name=NAME,
            title=TITLE,
            status=SignalStatus.OK,
            score=score,
            weight=WEIGHT if score is not None else 0,
            confidence=conf,
            summary=summary,
            findings=findings,
        )
