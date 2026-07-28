# PF-ERI v2 reproducible work artifacts

This root contains reconstructable workspaces. GPU and ModelScope material is
under `gpu/`, pipeline staging is under `pipeline/`, and reviewer rehearsal or
annotation material is under `review/`. It is not a scientific result root.

Byte-identical copies of canonical frozen images have been removed and recorded
in `artifacts/manifests/pferi_v2_work_image_dedup.csv`. Restore them when a
self-contained package is required:

```bash
python scripts/materialize_pferi_v2_work_images.py
python scripts/materialize_pferi_v2_work_images.py --apply
```

The first command is a dry run. Restoration refuses missing or changed canonical
files and never overwrites a nonmatching work file.
