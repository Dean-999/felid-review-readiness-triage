#!/usr/bin/env python3
"""Mandatory five-pair PF-ERI execution-interface smoke gate."""
from __future__ import annotations
import argparse, csv, json, sys, zipfile
from pathlib import Path
import local_match_runner_v2 as runner

def main() -> int:
 p=argparse.ArgumentParser();p.add_argument("--package-zip",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args();out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
 try:
  with zipfile.ZipFile(a.package_zip) as z:z.extractall(out/"smoke_input")
  root=out/"smoke_input/v2_local_match_execution_package";pairs=list(csv.DictReader((root/"pair_execution_manifest.csv").open()))[:5]
  if len(pairs)!=5:raise RuntimeError("smoke manifest has fewer than five pairs")
  params=json.loads(runner.CONTRACT.read_text())["parameters"];models=runner._models(params)
 except Exception as error:
  report={"status":"FAIL","fatal_error":{"stage":"initialization","exception_type":type(error).__name__,"message":str(error)},"records":[]};(out/"smoke_test.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return 1
 records=[];errors=[]
 for pair in pairs:
  for direction,left,right in (("A_to_B",pair["left_asset_filename"],pair["right_asset_filename"]),("B_to_A",pair["right_asset_filename"],pair["left_asset_filename"])):
   runtime=[];row,provenance=runner.measure_direction_v2(pair["pair_execution_id"],direction,root/"images"/left,root/"images"/right,models,params,runtime)
   record={"pair_id":pair["pair_execution_id"],"direction":direction,"image_id":left,"decode_success":row["failure_code"]!="image_decode_failure","region_source":provenance.get("region_source",""),"region_shape":[row.get("source_region_area_px","")],"region_coverage":row.get("source_region_area_px",""),"keypoint_count_A":None,"keypoint_count_B":None,"raw_output_type":"","raw_output_keys":[],"raw_output_structure":{},"raw_tensor_shapes":{},"normalized_match_shape":[],"normalized_match_count":None,"ransac_input_source_shape":[],"ransac_input_target_shape":[],"ransac_inlier_count":None,"failure_code":row["failure_code"]}
   if runtime:
    record.update(runtime[-1]); errors.extend(runtime)
   else: record.update({k:provenance.get(k,record[k]) for k in record if k in provenance});record["raw_output_type"]=provenance.get("raw_output_type","");record["raw_output_keys"]=provenance.get("raw_output_keys",[]);record["raw_output_structure"]=provenance.get("raw_output_shapes",{});record["raw_tensor_shapes"]=provenance.get("raw_output_shapes",{});record["normalized_match_count"]=provenance.get("normalized_match_count");record["normalized_match_shape"]=[record["normalized_match_count"],2] if record["normalized_match_count"] is not None else [];record["ransac_input_source_shape"]=provenance.get("ransac_input_shape",[]);record["ransac_input_target_shape"]=provenance.get("ransac_input_shape",[])
   records.append(record);print(json.dumps(record,sort_keys=True))
 fatal=[e for e in errors if e.get("exception_type") in {"RuntimeError","AttributeError","TypeError"} or e.get("keypoint_count_A")==0 or e.get("keypoint_count_B")==0 or e.get("ransac_input_shape") not in ([],None) and (len(e["ransac_input_shape"])!=2 or e["ransac_input_shape"][1]!=2)]
 report={"status":"PASS" if not fatal else "FAIL","pair_count":5,"directional_record_count":len(records),"records":records,"fatal_errors":fatal}
 (out/"smoke_test.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return 0 if not fatal else 1
if __name__=="__main__":raise SystemExit(main())
