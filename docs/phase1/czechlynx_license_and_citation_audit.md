# CzechLynx License and Citation Audit

## Purpose

This document tracks license, citation, and image-display readiness for the CzechLynx dataset used as the quantitative known-ID validation carrier in this project.

The local CzechLynx dataset has been downloaded and used for an internal 200-image blinded pilot triage. Source pages and license terms have been verified for the paper and Zenodo dataset record. **Paper license and dataset license are different** and must not be conflated.

## Applicable Project Rules

- CzechLynx is the quantitative known-ID validation carrier only.
- Do not commit raw images, contact sheets, `data/`, or `outputs/`.
- Do not expose sensitive location metadata in public materials.
- Do not make final scientific claims from license review alone.

## Project Relevance

CzechLynx supports known-ID validation in this project because it includes:

- verified individual IDs;
- real camera-trap images;
- metadata;
- masks and pose annotations (not used in the current pilot slice);
- evaluation splits.

**Current project use:** a 200-image real-image pilot sampled from 39,760 real images. Synthetic CzechLynx data is not used in the primary validation workflow.

This project evaluates review-readiness before Re-ID review. It does not claim to identify individual animals in deployment.

---

## Source 1: Scientific Data Paper (Primary Paper Citation)

| Field | Verified value |
| --- | --- |
| Role | Primary **paper** citation source |
| Citation | Picek, L., Straka, J., Jirik, M. et al. CzechLynx: A Dataset for Individual Identification and Pose Estimation of the Eurasian Lynx. *Scientific Data* **13**, 511 (2026). https://doi.org/10.1038/s41597-026-06853-9 |
| Article license | **CC BY-NC-ND 4.0** |
| Scope of article license | Applies to the **article text and figures**, not automatically to the dataset files |

### Paper BibTeX (placeholder for formal export)

```bibtex
@article{picek2026czechlynx,
  author  = {Picek, Luk{\'a}{\v{s}} and Straka, Jan and Jirik, Martin and others},
  title   = {CzechLynx: A Dataset for Individual Identification and Pose Estimation of the Eurasian Lynx},
  journal = {Scientific Data},
  volume  = {13},
  pages   = {511},
  year    = {2026},
  doi     = {10.1038/s41597-026-06853-9}
}
```

---

## Source 2: Zenodo Dataset (Primary Dataset DOI / License)

| Field | Verified value |
| --- | --- |
| Role | Primary **dataset** DOI and license source |
| Title | CzechLynx Dataset (v1.0) |
| DOI | https://doi.org/10.5281/zenodo.17592004 |
| Version | v1.0 |
| Published | 12 June 2025 |
| Resource type | Dataset |
| Dataset license (verified) | **Creative Commons Attribution 4.0 International (CC BY 4.0)** |

### Dataset Citation

Use the Zenodo-recommended dataset citation when citing the dataset files (not Kaggle as primary if Zenodo is available). Confirm exact author list and version string on the Zenodo record when preparing final references.

Example form (verify against Zenodo export):

> CzechLynx Dataset (v1.0). Zenodo. https://doi.org/10.5281/zenodo.17592004

### CC BY 4.0 Requirements (Dataset Files)

For dataset files under CC BY 4.0:

- provide **attribution** and a **license link**;
- if images are modified or cropped for display, **indicate modification** where required.

These are legal requirements for reuse of dataset content. They do not override this project's conservative display policy below.

---

## Source 3: Kaggle (Mirror / Download)

| Field | Value |
| --- | --- |
| Role | Mirror and download source; example notebooks may be listed there |
| Primary citation? | **No** — prefer Zenodo DOI and Scientific Data paper for formal citation |
| Notes | Useful for access convenience; not the authoritative license record for the dataset files |

Record the Kaggle dataset page URL in project notes when needed for reproducibility of download path. Do not treat Kaggle as replacing Zenodo for dataset licensing.

**Kaggle citation (secondary):** If a mirror page must be cited for download reproducibility, label it explicitly as a mirror (e.g., "CzechLynx dataset, Kaggle mirror, accessed [date]") and still cite the Zenodo DOI and Scientific Data paper as primary references.

---

## Citation Quick Reference

**Paper (primary for the publication):**

Picek, L., Straka, J., Jirik, M. et al. CzechLynx: A Dataset for Individual Identification and Pose Estimation of the Eurasian Lynx. *Scientific Data* **13**, 511 (2026). https://doi.org/10.1038/s41597-026-06853-9

**Dataset (primary for the dataset files):**

CzechLynx Dataset (v1.0). Zenodo. https://doi.org/10.5281/zenodo.17592004

**Kaggle (mirror only, if needed):**

CzechLynx dataset — Kaggle mirror (download path). Not the primary dataset citation; pair with Zenodo DOI and paper citation above.

---

## License Separation (Critical)

| Asset | License | What it governs |
| --- | --- | --- |
| Scientific Data article | CC BY-NC-ND 4.0 | Article text and article figures |
| Zenodo dataset files | CC BY 4.0 | Dataset files (images and associated dataset release) |

**Do not assume** the paper's CC BY-NC-ND terms apply to the dataset files. **Do not assume** CC BY 4.0 on the dataset relaxes requirements for the article itself.

---

## License Audit Table

| Use Case | Dataset license (CC BY 4.0) | Project policy (this repo) |
| --- | --- | --- |
| Internal research use with citation | Allowed with attribution | **Allowed** — required citation to paper and Zenodo dataset |
| Mentor-only private slides (minimal examples) | Allowed if attributed | **Allowed** — keep examples minimal; attribute; avoid sensitive metadata |
| Science fair / poster sample images | Allowed if attributed; indicate modification if cropped | **Allowed with caution** — attribute; avoid coordinates, trap IDs, cell codes, and sensitive locations |
| GitHub README or public repo images | Legally possible under CC BY 4.0 with attribution | **Not used in this project for now** — project policy: no raw image display in public repo |
| Raw image redistribution in this repo | Not permitted by project regardless of mirror convenience | **Do not redistribute** — no raw images in Git |
| Public contact sheets | Not a separate license category; treated as image display | **Do not release** contact sheets publicly |
| Publish coordinates, trap IDs, cell codes, exact locations | Not a license substitute for privacy/ethics | **Do not publish** sensitive location metadata |

---

## Current Decision Summary

| Topic | Decision |
| --- | --- |
| Internal research use | **Allowed with citation** (paper + Zenodo dataset) |
| Mentor-only slide use | **Allowed if attributed**; keep minimal |
| Poster sample image use | **Allowed if attributed**; avoid sensitive metadata; note modifications if cropped |
| GitHub README / public image display | CC BY 4.0 may permit attributed display in principle; **project policy: no raw image display in public materials for now** |
| Raw image redistribution | **Do not redistribute** in this repository |
| Contact sheet public release | **Do not release** |
| Sensitive metadata | **Do not publish** coordinates, trap IDs, cell codes, or sensitive camera locations |

---

## Risk Rules

- Do not commit images or contact sheets.
- Do not commit `data/` or `outputs/`.
- Do not publish exact coordinates or sensitive camera locations.
- Do not expose `unique_name`, original `lynx_###` paths, latitude, longitude, exact location, `cell_code`, or `trap_id` in blinded review or public materials.
- Keep internal mapping files separate from blinded label files.
- Prefer Zenodo + paper citations over Kaggle for formal attribution.

---

## To-Verify Checklist

- [x] Confirm Scientific Data paper URL and citation.
- [x] Record paper license (CC BY-NC-ND 4.0) and scope (article only).
- [x] Confirm Zenodo DOI, version, and dataset license (CC BY 4.0).
- [ ] Export final Zenodo citation string from the record (author list, version line).
- [ ] Record Kaggle mirror URL for download reproducibility (optional).
- [ ] Record access date for each source page in the table below.
- [ ] Re-check Zenodo if a new dataset version is released.

---

## Verified Source Log

| Date Checked | Source | Link | Finding |
| --- | --- | --- | --- |
| Pending | Scientific Data paper | https://doi.org/10.1038/s41597-026-06853-9 | Article CC BY-NC-ND 4.0; primary paper citation |
| Pending | Zenodo dataset v1.0 | https://doi.org/10.5281/zenodo.17592004 | Dataset CC BY 4.0; primary dataset DOI/license |
| Pending | Kaggle mirror | Add URL when recorded | Download mirror; not primary citation source |

Replace "Pending" access dates when recorded in the project log.
