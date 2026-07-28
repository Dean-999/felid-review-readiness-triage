# Task 05: v2 Blinded Reviewer-Interface Dry Run and Leakage Audit

Status: PASS. Machine preparation/static audit and the independent browser audit have both passed. This was the final hard Workstream 02 gate before any real v2 outcome collection.

## Purpose

The dry run tests whether the rendered v2 reviewer interface preserves the outcome-export fence in a real browser. It is not a small outcome study and must not generate, import, or interpret a real review label. The only permitted inputs are a deterministic twelve-pair subset of the outcome-free measurement-feasibility pilot. Those pilot pairs are permanently excluded from both confirmation samples, so their use cannot contaminate the future confirmation estimate.

## Boundary and packet design

The reviewer-visible packet has exactly five fields: neutral packet identifier, two opaque rendered-asset tokens, instrument version, and review-form schema version. Images are rendered into opaque token-named PNG files without original filenames or image metadata. The restricted linkage and restricted asset map are physically outside the reviewer-view directory. A raw response template can record only the packet identifier, a raw response identifier, decision, reason codes, confidence, optional note, timestamp, and a technical-problem flag. It cannot hold a canonical pair identifier, source image identifier, feature, descriptor, score, rank, route, identity value, prior response, majority label, adjudication, or model-ready recode.

## Required evidence

The build must pass a static audit of public files, headers, opaque asset names, selection provenance, and view-directory isolation. A non-reviewer who will not become a first-pass reviewer must then inspect the live rendered interface. The inspection covers visible DOM content, URLs and browser history/state, asset tokens and filenames, downloadable exports, sort/filter/search controls, network or hidden fields, and isolation of peer/adjudicator responses. Any exposure invalidates the dry run and requires a documented remediation and retest. A static audit is necessary but cannot substitute for this independent browser inspection.

The prepared package is `work/pferi_v2/review/interface_dry_run/`. Its machine static audit passes for twelve deterministic pilot pairs and twenty-four opaque rendered assets. The only package shared with the independent auditor was `independent_browser_audit/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY.zip`, containing the reviewer view, blank checklist, and Chinese auditor guide but no restricted linkage.

The completed return is archived under `independent_browser_audit/returned_audits/2026-07-14_a001_completed/`. Its delivery ZIP SHA-256 is `0d16fa193502f4277e066c1f47ccc0cd6aac0b0e0e0ae3d1bb3164f9fcf63962`. The validator passed all eight required checks for independent auditor `A001`, with `exposure_detected = no` and final disposition `no_leak_confirmed`. The returned public reviewer view contains the same twenty-eight files as the official v3 release and is byte-identical file by file. The machine recheck, validated human checklist, and final consolidated audit are retained with that archive.

## Exit decision

The dry run passes only when the machine audit passes and the independent auditor documents zero prohibited exposures for every required browser check. A pass permits construction of the real blinded outcome packet in the next workstream; it does not itself authorize outcome collection until the packet-specific preflight is also completed. A fail preserves the outcome-free status of the project and requires interface remediation, never relabeling or deleting evidence of the leak.
