# PF-ERI v2 transfer artifacts

This directory holds transport ZIPs used for GPU, browser-audit or handoff
workflows. These archives are delivery media, not canonical scientific results.

Canonical inputs live under `data/frozen/pferi_v2/`, generated results under
`outputs/pferi_v2/`, and extracted/reconstructable workspaces under
`work/pferi_v2/`. ZIP retention may therefore be managed independently once its
corresponding audit, hash and extracted result have been verified.

The full-frame local-match family has one current control archive:

- `PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip`
- audit: `PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.audit.json`
- builder: `scripts/build_v2_full_frame_local_match_control_package.py`

Kaggle and Colab use that same archive. Platform names, continuation attempts,
and retries do not create additional retained ZIP versions. Original/returned
human-audit deliveries and input/result bundle pairs remain separate because
they document different sides of a provenance handoff.
