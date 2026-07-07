# legacy-code19 Bobcat Source Reset: iNaturalist Daylight/Nonblur Queue

Date: 2026-07-06

## Decision

The previous legacy-code19 Bobcat camera-trap-derived review queues are deprecated for
clean-photo selection. They remain diagnostic artifacts only.

Reason: repeated human spot review showed night/IR images, motion blur, small
subjects, and unreliable detector area coverage. Area thresholds alone did not
solve the visual-quality problem.

## Replacement Source

The active Bobcat review source is now direct iNaturalist Research Grade,
annotation-aware material inherited from legacy-code17m:

- direct iNaturalist rows only;
- organism evidence required;
- scat/track rows excluded;
- dead/captive rows excluded;
- GBIF iNaturalist mirrors are not used as the preferred clean source.

## legacy-code19 Clean Queue

Script:

```text
scripts/build_legacy-code19_bobcat_inat_daylight_clean_queue.py
```

Primary output:

```text
outputs/legacy-code19/legacy-code19_bobcat_inat_daylight_clean_queue/legacy-code19_bobcat_inat_daylight_nonblur_review_queue.csv
```

Audit:

```text
outputs/legacy-code19/legacy-code19_bobcat_inat_daylight_clean_queue/legacy-code19_bobcat_inat_daylight_nonblur_queue_audit.json
```

Deprecated camera-trap manifest:

```text
outputs/legacy-code19/legacy-code19_bobcat_inat_daylight_clean_queue/legacy-code19_camera_trap_queue_deprecation_manifest.json
```

Current result:

- input legacy-code17m scored rows: 10,229;
- deduplicated image URLs: 10,221;
- selected daylight/nonblur review rows: 3,138;
- tier1 high-resolution daylight/nonblur rows: 661;
- tier2 daylight/nonblur review rows: 2,477.

## Selection Rule

The clean queue keeps direct iNaturalist candidates only when all of the
following proxy gates pass:

- legacy-code17m seed tier is `strict_pass` or `near_strict`;
- colorfulness proxy is at least 20;
- dark clipping fraction is at most 0.18;
- bright clipping fraction is at most 0.18;
- contrast standard deviation is at least 45;
- gradient p90 is at least 20;
- Laplacian variance is at least 160;
- entropy is at least 5.

Tier1 additionally requires:

- minimum image dimension at least 900;
- at least 1.2 megapixels;
- downloaded image size at least 120,000 bytes;
- no prior legacy-code17m proxy reject reasons.

## Review App

The active app is:

```text
scripts/streamlit_legacy-code19_inat_clean_review_app.py
```

Current local URL:

```text
http://127.0.0.1:8514
```

The app is intentionally minimal: image, source links, decision controls, and
collapsed details only.

## Claim Boundary

This queue is a cleaner review source, not a final algorithm-ready dataset.
Final Bobcat inclusion still requires human `CLEAR`.
