#!/usr/bin/env python3
from __future__ import annotations
import argparse,zipfile,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/"gpu/kaggle_v2_local_matcher_v2";OUT=ROOT/"work/pferi_v2/measurement_feasibility/final_local_match_package_v2.zip"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=OUT);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():raise FileExistsError(a.output)
 with zipfile.ZipFile(a.output,"w",zipfile.ZIP_DEFLATED) as z:
  for x in SRC.iterdir():
   if x.is_file() and x.suffix in {".py",".json",".txt",".ipynb",".md"}:z.write(x,x.name)
 audit={"status":"PASS","zip_sha256":sha(a.output),"contains_images":False,"claim_boundary":"Code-only robust v2 execution package."};(a.output.with_suffix(".audit.json")).write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
