#!/usr/bin/env python3
"""Return FINAL_VALIDATION_PASS only for a complete, nonzero PF-ERI v2 run."""
from __future__ import annotations
import argparse, json
from check_local_match_results_v2 import check_results
def main():
 p=argparse.ArgumentParser();p.add_argument("--output-dir",required=True);a=p.parse_args();audit=check_results(a.output_dir);errors=list(audit["error_codes"])
 if audit["successful_pairs"]<=0:errors.append("no_successful_pairs")
 if audit["valid_measurement_rate"]<=0:errors.append("nonpositive_valid_measurement_rate")
 if audit["freeze_hash_verification"]!="PASS":errors.append("freeze_hash_not_pass")
 try:
  if json.loads(open(f"{a.output_dir}/smoke_test.json").read()).get("status")!="PASS":errors.append("smoke_test_not_pass")
 except FileNotFoundError: errors.append("smoke_test_missing")
 try:
  runtime_errors=json.loads(open(f"{a.output_dir}/runtime_errors.json").read())
  if runtime_errors:errors.append("runtime_errors_not_empty")
 except FileNotFoundError: errors.append("runtime_errors_missing")
 audit["final_validation_status"]="FINAL_VALIDATION_PASS" if not errors else "FINAL_VALIDATION_FAIL";audit["final_validation_errors"]=errors;print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
