# PF-ERI v2 experiment-iteration lineage

This record preserves the meaning and raw SHA-256 values of superseded machine
artifacts removed from the active v2 tree on 18 July 2026. Current scientific
results remain under `outputs/pferi_v2`; delivery media remain under
`artifacts/transfers/pferi_v2`.

## Structural-oracle reliability

| artifact | status | SHA-256 | disposition |
| --- | --- | --- | --- |
| `structural_oracle_reliability_audit.json` | `measurement_not_ready` | `21d5afa24081c198dd1a2b9210f939a1583689d2e97e5630996ad049142b8c0a` | superseded initial calculation |
| `structural_oracle_reliability_audit_v2.json` | `measurement_not_ready` | `d8f44251b20f48cf765da4f06c4fc5bcc07a283ce107174b9b730ffa00ae6b03` | superseded intermediate calculation |
| `structural_oracle_reliability_audit_latest.json` | `PASS` | `140d2c2dfd1581246e375570ed9978da744329e99c73dc1efdcacf0e070b8244` | retained current result |

The current result uses the corrected frozen weighted-kappa/bootstrap gate. The
two older files are preserved by this lineage record and Git history, not as
parallel current conclusions.

## Robust local matcher

| artifact | SHA-256 | disposition |
| --- | --- | --- |
| `v2_local_match_package_audit.json` | `4a3def0e64ed355977e22eb1dc36a930feb548d0093fd729e4d811d3303d1835` | superseded initial package audit |
| `v2_local_match_kaggle_package_audit.json` | `4e07b24c789c9b2c00584e30c45007adc856406d21005c77d52b1c65c5e593c5` | superseded matcher-v1 Kaggle package audit |
| `final_local_match_package_v2.audit.json` | `d655796312b7841ace3d412ce7cb79424fa78890cef0865c21a855e8591824b4` | retained accepted package audit |

The removed extracted work runner had SHA-256
`101feb0354c79fec095ce46570a82c523b550ece227da45ffb3aa4cf9bc1a3e0`.
The retained runner at `gpu/kaggle_v2_local_matcher_v2/local_match_runner_v2.py`
has SHA-256
`e3e2924d114f30f6134f1c4ec0b849dff15e3b9d440faaf3cbb5206e31f3885a`
and adds `extrasaction="ignore"` to robust CSV output plus the later full-frame
wrapper package.

## Reviewer-interface dry run

The original and returned delivery ZIPs each contain 30 substantive files. Of
those, 29 are byte-identical; only `human_browser_leakage_checklist.csv` changed
from the blank 787-byte form to the completed 1,802-byte return. Both ZIPs are
retained as the handoff record. The duplicate original unpacked `reviewer_view`
and the byte-identical `machine_static_audit_recheck.json` are reconstructable
work copies and were removed.
