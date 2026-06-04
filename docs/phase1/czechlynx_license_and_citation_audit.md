# CzechLynx License and Citation Audit

## Purpose

This document tracks license, citation, and image-display readiness for the CzechLynx dataset used as the quantitative known-ID validation carrier in this project.

The local CzechLynx dataset has been downloaded and used for an internal 200-image blinded pilot triage. This document does not confirm public display, redistribution, or GitHub release permission. Those permissions remain pending until the original dataset terms and source pages are verified.

## Confirmed Facts

- CzechLynx is used in this project as the quantitative known-ID validation carrier.
- The project evaluates image review-readiness before individual-level Re-ID review.
- The project does not claim to identify individual animals.
- The project must not publish or redistribute CzechLynx images, contact sheets, raw image paths, exact coordinates, or sensitive camera locations unless permission is confirmed.

## Dataset Source Fields

| Field | Status | Notes |
| --- | --- | --- |
| Kaggle dataset page | Pending verification | Add source URL after web/source check. |
| Scientific Data / paper page | Pending verification | Add journal or publisher URL after source check. |
| Dataset authors | Pending verification | Record exact author list from dataset page and/or paper. |
| Access date | Pending verification | Record the date the source page and license terms are checked. |

## Citation Fields

| Field | Status | Notes |
| --- | --- | --- |
| Dataset citation | Pending verification | Use the citation requested by the official dataset page. |
| Paper citation | Pending verification | Use the paper citation from the publisher page. |
| BibTeX placeholder | Pending verification | Replace placeholder only after confirming source metadata. |

### BibTeX Placeholder

```bibtex
@misc{czechlynx_dataset_pending,
  title = {CzechLynx dataset citation pending verification},
  author = {Dataset authors pending verification},
  year = {Year pending verification},
  note = {Do not use for final citation until official source metadata is confirmed}
}
```

## License Audit Table

| Use Case | Current Status | Decision |
| --- | --- | --- |
| Research use | Pending confirmation | Likely allowed only after citation and license terms are checked. |
| Redistribution | Pending confirmation | Do not redistribute until explicitly confirmed. |
| Public display of sample images | Pending | Do not display publicly until explicitly confirmed. |
| Public display of contact sheets | Pending | Do not display publicly until explicitly confirmed. |
| GitHub public release | Pending | Do not include images, contact sheets, raw paths, or sensitive metadata. |
| Science fair poster use | Pending | Do not include images until public display permission is confirmed. |
| Mentor-only private slide use | Pending | Treat as private/internal only; still verify license and display terms before use. |

## Current Decision

- Internal research use: pending confirmation / likely allowed only after citation check.
- Public image display: pending.
- Raw image redistribution: no until confirmed.
- Contact sheet redistribution or display: no until confirmed.
- Public GitHub release of images or derived image sheets: no until confirmed.

## Risk Rules

- Do not commit images.
- Do not commit contact sheets.
- Do not commit `data/` or `outputs/`.
- Do not publish exact coordinates.
- Do not publish sensitive camera locations.
- Do not expose `unique_name`, original `lynx_###` paths, latitude, longitude, exact location, `cell_code`, or `trap_id` in blinded review materials.
- Keep internal mapping files separate from blinded label files.
- Do not make public display claims until source terms are checked and recorded.

## To-Verify Checklist

- [ ] Confirm the official Kaggle dataset page URL.
- [ ] Confirm the official Scientific Data / paper page URL.
- [ ] Record exact dataset authors.
- [ ] Record exact paper authors.
- [ ] Record required dataset citation.
- [ ] Record required paper citation.
- [ ] Record official license text or license identifier.
- [ ] Check whether internal research use is permitted.
- [ ] Check whether raw image redistribution is permitted.
- [ ] Check whether public display of individual sample images is permitted.
- [ ] Check whether public display of contact sheets is permitted.
- [ ] Check whether science fair poster image display is permitted.
- [ ] Check whether mentor-only private slides are permitted.
- [ ] Record access date for each source page.

## Notes for Future Web-Verified Source Links

Add verified source links and notes here after checking official dataset and paper pages.

| Date Checked | Source | Link | Finding | Remaining Question |
| --- | --- | --- | --- | --- |
| Pending | Kaggle dataset page | Pending | Pending | Confirm license, citation, and display terms. |
| Pending | Scientific Data / paper page | Pending | Pending | Confirm citation and any reuse guidance. |
