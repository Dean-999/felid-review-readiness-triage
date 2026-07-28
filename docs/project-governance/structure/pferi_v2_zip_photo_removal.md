# PF-ERI v2 ZIP Photo Removal Record

Execution date: 2026-07-28

## Decision

Fifty-three PF-ERI v2 delivery and execution ZIP files contain reproducible copies of animal photographs. Their control records are scientifically important, but retaining another 41.2 GB copy of the image payload is not necessary because each group has a verified source manifest, restricted asset map, builder, or retained source directory.

The approved cleanup converts these ZIP files into metadata-only preservation copies. It removes only image members with the extensions `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`, `.bmp`, or `.gif`. It preserves CSV, JSON, README, audit, contract, mapping, response, and result members.

## Execution Result

The cleanup completed for all 53 approved ZIP files. It removed 26,482 image members and reduced the approved ZIP set from 41,227,208,493 bytes to 2,063,080 bytes, reclaiming 41,225,145,413 bytes (41.225 GB, or 38.394 GiB).

Post-cleanup verification found zero image members, zero CRC failures, zero missing `PHOTOS_REMOVED.md` records, zero manifest hash mismatches, and zero mismatches across the 54 checksum references that point to rebuilt ZIP files.

## Scope

| Group | ZIP count | Provenance retained |
| --- | ---: | --- |
| Formal reviewer full packages | 4 | `scripts/build_v2_formal_reviewer_packages.py`, restricted asset map, `data/frozen/pferi_v2/` |
| Formal reviewer subpackages | 32 | `SUBPACKAGE_MANIFEST.csv`, `subpackage_audit.json`, and the full-package mappings |
| Task 15I reviewer packages | 4 | restricted asset map and `data/candidate-reservoirs/task15i_independent_lynx_v1/images/` |
| Task 15L calibration reviewer packages | 4 | selected-image execution manifest and restricted asset map |
| Adjudication packages | 4 | adjudication builder, audit, returned decisions, and final outcomes |
| Task 15I descriptor image package | 1 | `descriptor_execution_manifest.csv` and the controlled reservoir |
| Task 15K and Task 15M ModelScope packages | 2 | selected-image manifests, package builders, and retained source images |
| Original and returned interface-audit deliveries | 2 | browser-audit builder and extracted audit workspace |

Excluded from this cleanup are PF-ERI v1 packages, CzechLynx annotation-batch ZIP files, all source images under `data/`, reviewer responses, adjudicated outcomes, calibration/confirmation results, restricted mappings, and final freeze artifacts.

## Audit Trail

The machine-readable record is `artifacts/manifests/pferi_v2_zip_photo_removal.csv`. For every ZIP it records the original size and SHA256, removed photo counts and bytes, source provenance, the rebuilt size and SHA256, and measured reclaimed bytes.

Each rebuilt ZIP contains `PHOTOS_REMOVED.md` with its original SHA256 and reconstruction source. Historical internal manifests may still name the removed image members; this is intentional because those manifests preserve the original delivery contract.

The operation is implemented by `scripts/strip_pferi_v2_zip_photos.py`. It writes a temporary ZIP in the same directory, checks every retained member CRC, verifies that no image member remains, and only then atomically replaces the original ZIP. Directly affected checksum declarations are updated to the rebuilt hashes; original hashes remain in the removal manifest.

Some broad historical `CHECKSUMS.sha256` inventories also list extracted package directories moved to the macOS Trash during the earlier `A1-A8` cleanup. A full check of those historical inventories therefore reports missing extracted files. This does not indicate a rebuilt ZIP failure; the ZIP-specific checksum entries and all retained ZIP members were verified separately.
