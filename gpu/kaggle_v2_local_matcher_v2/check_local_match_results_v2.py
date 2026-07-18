#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from collections import Counter
def check_results(out):
 out=Path(out);d=list(csv.DictReader((out/"directional_measurements.csv").open()));c=list(csv.DictReader((out/"canonical_measurements.csv").open()));p=list(csv.DictReader((out/"region_provenance.csv").open()));valid=[x for x in c if x["value_status"]=="not_missing"];vals=[float(x["local_match_coverage_fraction"]) for x in valid]; errors=[]
 if len(d)!=320:errors.append("directional_row_count_not_320")
 if len(c)!=160:errors.append("canonical_row_count_not_160")
 if len(p)!=320:errors.append("provenance_row_count_not_320")
 freeze=out/"matcher_freeze_record.json";freeze_ok=freeze.exists() and json.loads(freeze.read_text()).get("runner_sha256")
 if not freeze_ok:errors.append("freeze_hash_verification_failed")
 if not errors and len(valid)==len(c) and len(c)>0: status="PASS"
 elif not errors and len(valid)>0: status="PARTIAL"
 else: status="FAIL"
 return {"status":status,"total_pairs":len(c),"successful_pairs":len(valid),"valid_measurement_rate":len(valid)/len(c) if c else 0,"directional_row_count":len(d),"canonical_row_count":len(c),"failure_distribution":dict(Counter(x["failure_code"] for x in c if x["value_status"]!="not_missing")),"region_source_distribution":dict(Counter(x["region_source"] for x in p)),"coverage_statistics":{"mean":sum(vals)/len(vals) if vals else None,"median":sorted(vals)[len(vals)//2] if vals else None,"min":min(vals) if vals else None,"max":max(vals) if vals else None},"freeze_hash_verification":"PASS" if freeze_ok else "FAIL","manual_rescue_count":sum(int(x.get("manual_rescue_count",0)or 0) for x in d),"error_codes":errors}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output-dir",required=True);a=p.parse_args();print(json.dumps(check_results(a.output_dir),indent=2))
if __name__=="__main__":main()
