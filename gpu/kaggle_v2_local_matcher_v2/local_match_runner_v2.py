#!/usr/bin/env python3
"""PF-ERI v2 robust local matching: frozen regions, SuperPoint, LightGlue, RANSAC."""
from __future__ import annotations
import argparse,csv,hashlib,json,platform,sys,time,zipfile
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import cv2,numpy as np
from PIL import Image,ImageOps
HERE=Path(__file__).resolve().parent; CONTRACT=HERE/"local_match_execution_protocol_v2.json"; FREEZE="matcher_freeze_record.json"
DIRECTIONAL_COLUMNS=["pair_execution_id","direction","source_asset_filename","target_asset_filename","local_match_coverage_fraction","value_status","failure_code","source_region_area_px","target_region_area_px","inlier_count","runtime_seconds","manual_rescue_count"]
CANONICAL_COLUMNS=["pair_execution_id","local_match_coverage_fraction","value_status","failure_code","a_to_b_coverage_fraction","b_to_a_coverage_fraction","pair_runtime_seconds","manual_rescue_count"]
DEFAULT_PARAMETERS={"max_image_dimension":1600,"fallback_min_area_fraction":.03,"fallback_max_area_fraction":.95,"animal_score_threshold":.5,"mask_threshold":.5,"superpoint_max_num_keypoints":2048,"superpoint_detection_threshold":.005,"lightglue_filter_threshold":.1,"level_2_filter_threshold":.05,"ransac_reprojection_threshold_px":5.,"minimum_ransac_inliers":4,"coverage_disc_radius_fraction_of_smaller_region_diagonal":.01}
class MeasurementFailure(ValueError):
 def __init__(self,code,diagnostic): super().__init__(code);self.code=code;self.diagnostic=diagnostic
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256();
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def valid_row(direction,v): return {"direction":direction,"local_match_coverage_fraction":v,"value_status":"not_missing","failure_code":"none","runtime_seconds":0,"manual_rescue_count":0}
def failed_row(direction,code): return {"direction":direction,"local_match_coverage_fraction":"","value_status":"model_inference_failure","failure_code":code,"runtime_seconds":0,"manual_rescue_count":0}
def output_diagnostic(output):
 if isinstance(output,(list,tuple)): return {"type":type(output).__name__,"length":len(output),"items":[output_diagnostic(x) for x in output[:1]]}
 if isinstance(output,dict): return {"type":"dict","keys":sorted(output),"items":{k:output_diagnostic(v) for k,v in output.items() if k in {"matches","matches0","matches01"}}}
 return {"type":type(output).__name__,"shape":list(getattr(output,"shape",[]))}
def parse_matcher_output(output, tensor_type=None, trace=None):
 """Recursively unwrap LightGlue containers, then return np.int64[K,2]."""
 if tensor_type is None:
  import torch; tensor_type=torch.Tensor
 raw=output_diagnostic(output); trace=[] if trace is None else trace; selected_key=""
 while not isinstance(output,tensor_type):
  if isinstance(output,(list,tuple)):
   trace.append({"container":type(output).__name__,"length":len(output)})
   if not output: raise RuntimeError(f"empty LightGlue container; trace={trace}; raw={raw}")
   output=output[0]; continue
  if isinstance(output,dict):
   trace.append({"container":"dict","keys":sorted(output)})
   for key in ("matches","matches01","matches0"):
    if key in output: output=output[key]; selected_key=key; break
   else:
    if len(output)==1: output=next(iter(output.values()))
    else: raise RuntimeError(f"unsupported LightGlue dict; trace={trace}; raw={raw}")
   continue
  raise RuntimeError(f"non-tensor LightGlue leaf type={type(output).__name__}; trace={trace}; raw={raw}")
 trace.append({"container":"tensor","shape":list(getattr(output,"shape",[])),"selected_key":selected_key})
 array=output.detach().cpu().numpy()
 if selected_key=="matches0":
  array=np.squeeze(array)
  if array.ndim!=1: raise RuntimeError(f"matches0 must normalize to [N]; raw={raw}")
  indices=np.arange(array.shape[0],dtype=np.int64); keep=array>=0; return np.stack((indices[keep],array[keep]),axis=1).astype(np.int64,copy=False)
 array=np.squeeze(array,axis=0) if array.ndim==3 and array.shape[0]==1 else array
 if array.ndim!=2 or array.shape[1]!=2: raise RuntimeError(f"matches must normalize to [K,2]; raw={raw}; normalized_shape={array.shape}")
 return array.astype(np.int64,copy=False)
def select_region(image,detector_mask,params):
 if detector_mask is not None and detector_mask.any(): return detector_mask.astype(bool),"detector",{"fallback_reason":""}
 gray=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY); _,fg=cv2.threshold(cv2.GaussianBlur(gray,(5,5),0),0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU); fg=cv2.morphologyEx(fg,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
 n,lab,stats,cents=cv2.connectedComponentsWithStats(fg); h,w=gray.shape; candidates=[]
 for i in range(1,n):
  x,y,bw,bh,area=stats[i]; frac=area/(h*w); cx,cy=cents[i]; centre=1-min(1,((cx-w/2)/(w/2))**2+((cy-h/2)/(h/2))**2)
  if params["fallback_min_area_fraction"]<=frac<=params["fallback_max_area_fraction"]: candidates.append((area*(.5+.5*centre),x,y,bw,bh))
 if candidates:
  _,x,y,bw,bh=max(candidates); mask=np.zeros((h,w),bool); mask[y:y+bh,x:x+bw]=True; return mask,"fallback_bbox",{"fallback_reason":"detector_missing_or_invalid"}
 return np.ones((h,w),bool),"full_image",{"fallback_reason":"no_valid_foreground_component"}
def canonicalize(pid,a,b):
 base={"pair_execution_id":pid,"a_to_b_coverage_fraction":a.get("local_match_coverage_fraction",""),"b_to_a_coverage_fraction":b.get("local_match_coverage_fraction",""),"pair_runtime_seconds":round(float(a.get("runtime_seconds",0))+float(b.get("runtime_seconds",0)),6),"manual_rescue_count":0}
 if a["value_status"]!="not_missing" or b["value_status"]!="not_missing":
  z=a if a["value_status"]!="not_missing" else b; return {**base,"local_match_coverage_fraction":"","value_status":z["value_status"],"failure_code":z["failure_code"]}
 return {**base,"local_match_coverage_fraction":min(float(a["local_match_coverage_fraction"]),float(b["local_match_coverage_fraction"])),"value_status":"not_missing","failure_code":"none"}
def _models(p):
 import torch
 from lightglue import SuperPoint,LightGlue
 from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights,maskrcnn_resnet50_fpn_v2
 d=torch.device("cuda" if torch.cuda.is_available() else "cpu"); wt=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT; m=maskrcnn_resnet50_fpn_v2(weights=None,weights_backbone=None).to(d).eval();m.load_state_dict(wt.get_state_dict(progress=True,check_hash=True)); e=SuperPoint(max_num_keypoints=p["superpoint_max_num_keypoints"],detection_threshold=p["superpoint_detection_threshold"]).eval().to(d); return m,e,d
def _image(path,maxd,gray=False):
 with Image.open(path) as im:a=np.array(ImageOps.exif_transpose(im).convert("RGB"))
 if gray:
  g=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY);a=cv2.cvtColor(cv2.normalize(g,None,0,255,cv2.NORM_MINMAX),cv2.COLOR_GRAY2RGB)
 h,w=a.shape[:2];s=min(1,maxd/max(h,w));return cv2.resize(a,(round(w*s),round(h*s)),interpolation=cv2.INTER_AREA) if s<1 else a
def _detect(model,device,image,p):
 import torch
 x=torch.from_numpy(image.copy()).permute(2,0,1).float().div(255).to(device)
 with torch.inference_mode():r=model([x])[0]
 best=None
 for i,(l,s) in enumerate(zip(r["labels"].tolist(),r["scores"].tolist())):
  if l==17 and s>=p["animal_score_threshold"]:
   q=r["masks"][i,0].detach().cpu().numpy()>=p["mask_threshold"];best=q if best is None or q.sum()>best.sum() else best
 return best
def _attempt(src,dst,sm,tm,extractor,device,p,level):
 import torch
 from lightglue import LightGlue
 from lightglue.utils import numpy_image_to_torch
 matcher=LightGlue(features="superpoint",filter_threshold=p["lightglue_filter_threshold"] if level==1 else p["level_2_filter_threshold"]).eval().to(device); a=extractor.extract(numpy_image_to_torch(src).to(device));b=extractor.extract(numpy_image_to_torch(dst).to(device));raw=matcher({"image0":a,"image1":b});match=parse_matcher_output(raw);diagnostic={"keypoint_count_A":int(a["keypoints"].shape[-2]),"keypoint_count_B":int(b["keypoints"].shape[-2]),"raw_output_type":type(raw).__name__,"raw_output_keys":sorted(raw) if isinstance(raw,dict) else [],"raw_output_shapes":output_diagnostic(raw),"normalized_match_count":int(match.shape[0]),"ransac_input_shape":[int(match.shape[0]),2]}
 if match.shape[0]<4: raise MeasurementFailure("insufficient_matches",diagnostic)
 k0=a["keypoints"].detach().cpu().numpy()[0][match[:,0]];k1=b["keypoints"].detach().cpu().numpy()[0][match[:,1]];_,ins=cv2.findFundamentalMat(k0,k1,cv2.FM_RANSAC,p["ransac_reprojection_threshold_px"],.99)
 if ins is None or int(ins.sum())<p["minimum_ransac_inliers"]:raise MeasurementFailure("insufficient_inliers",diagnostic)
 rad=max(1,round(min(sm.sum()**.5,tm.sum()**.5)*p["coverage_disc_radius_fraction_of_smaller_region_diagonal"]));support=np.zeros(sm.shape,np.uint8)
 for x,y in k0[ins.ravel().astype(bool)].astype(int):cv2.circle(support,(int(x),int(y)),rad,1,-1)
 diagnostic["ransac_inlier_count"]=int(ins.sum());return float(np.logical_and(support.astype(bool),sm).sum()/sm.sum()),int(ins.sum()),diagnostic
def measure_direction_v2(pid,direction,source,target,models,p,runtime_errors=None):
 started=time.perf_counter();model,extractor,device=models; base={"pair_execution_id":pid,"direction":direction,"source_asset_filename":source.name,"target_asset_filename":target.name,"manual_rescue_count":0}
 try:
  rgb1,rgb2=_image(source,p["max_image_dimension"]),_image(target,p["max_image_dimension"]);sm,ss,meta=select_region(rgb1,_detect(model,device,rgb1,p),p);tm,ts,_=select_region(rgb2,_detect(model,device,rgb2,p),p)
 except Exception:return {**failed_row(direction,"image_decode_failure"),**base,"source_region_area_px":"","target_region_area_px":"","inlier_count":"","runtime_seconds":round(time.perf_counter()-started,6)}, {"pair_execution_id":pid,"direction":direction,"region_source":"","retry_level":"level_3","fallback_reason":"decode_failure"}
 for level,gray in ((1,False),(2,True)):
  try:
   src,dst=(rgb1,rgb2) if not gray else (_image(source,p["max_image_dimension"],True),_image(target,p["max_image_dimension"],True));v,n,diag=_attempt(src,dst,sm,tm,extractor,device,p,level);row={**base,"local_match_coverage_fraction":round(v,8),"value_status":"not_missing","failure_code":"none","source_region_area_px":int(sm.sum()),"target_region_area_px":int(tm.sum()),"inlier_count":n,"runtime_seconds":round(time.perf_counter()-started,6)};return row,{"pair_execution_id":pid,"direction":direction,"region_source":ss,"target_region_source":ts,"retry_level":f"level_{level}","fallback_reason":meta["fallback_reason"],**diag}
  except MeasurementFailure as error:
   last=error.code
   if runtime_errors is not None: runtime_errors.append({"pair_id":pid,"direction":direction,"stage":"measurement_gate","failure_code":error.code,"retry_level":f"level_{level}","exception_type":type(error).__name__,"message":str(error),**error.diagnostic})
  except Exception as error:
   last="model_runtime_error"
   if runtime_errors is not None: runtime_errors.append({"pair_id":pid,"direction":direction,"stage":"lightglue_matching","failure_code":"model_runtime_error","model":"SuperPoint+LightGlue","exception_type":type(error).__name__,"message":str(error),"retry_level":f"level_{level}","raw_output_type":"","raw_output_keys":[],"raw_output_shape":{},"normalized_match_count":None,"keypoint_count_A":None,"keypoint_count_B":None,"ransac_input_shape":[],"ransac_inlier_count":None})
 return {**base,"local_match_coverage_fraction":"","value_status":"model_inference_failure","failure_code":last,"source_region_area_px":int(sm.sum()),"target_region_area_px":int(tm.sum()),"inlier_count":"","runtime_seconds":round(time.perf_counter()-started,6)}, {"pair_execution_id":pid,"direction":direction,"region_source":ss,"target_region_source":ts,"retry_level":"level_3","fallback_reason":meta["fallback_reason"]}
def write_csv(path,fields,rows):
 with Path(path).open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
def freeze(out):
 import torch,torchvision
 p=json.loads(CONTRACT.read_text())["parameters"];m,e,d=_models(p);cache=Path(torch.hub.get_dir())/"checkpoints";env={"torch":torch.__version__,"torchvision":torchvision.__version__,"cuda":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"gpu_name":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"lightglue_version":getattr(__import__("lightglue"),"__version__","unknown")};record={"created_at_utc":now(),"protocol":"local_match_execution_protocol_v2","contract_sha256":sha(CONTRACT),"runner_sha256":sha(Path(__file__)),"weight_sha256":{x.name:sha(x) for x in cache.glob("*") if x.is_file()},"environment":env,"input_access":"forbidden_until_run"};Path(out).mkdir(parents=True,exist_ok=True);(Path(out)/FREEZE).write_text(json.dumps(record,indent=2));(Path(out)/"environment_report.json").write_text(json.dumps(env,indent=2));return record
def run(package_zip,out):
 out=Path(out);r=json.loads((out/FREEZE).read_text());
 if r["contract_sha256"]!=sha(CONTRACT):raise ValueError("freeze_hash_verification_failed")
 smoke=out/"smoke_test.json"
 if not smoke.is_file() or json.loads(smoke.read_text()).get("status")!="PASS":raise ValueError("mandatory_smoke_test_not_passed")
 with zipfile.ZipFile(package_zip) as z:z.extractall(out/"input")
 root=out/"input/v2_local_match_execution_package"; manifest_path=root/"pair_execution_manifest.csv"; images=root/"images"
 if not manifest_path.is_file() or not images.is_dir(): raise ValueError("invalid_input_package_layout")
 pairs=list(csv.DictReader(manifest_path.open()));
 if not pairs or len(list(images.iterdir())) < len({q for row in pairs for q in (row["left_asset_filename"],row["right_asset_filename"])}): raise ValueError("invalid_input_package_inventory")
 p=json.loads(CONTRACT.read_text())["parameters"];models=_models(p);ds=[];cs=[];prov=[];runtime_errors=[]
 for x in pairs:
  a,b=root/"images"/x["left_asset_filename"],root/"images"/x["right_asset_filename"]
  if not a.is_file() or not b.is_file(): raise ValueError(f"missing_manifest_image:{x['pair_execution_id']}")
  ab,pa=measure_direction_v2(x["pair_execution_id"],"A_to_B",a,b,models,p,runtime_errors);ba,pb=measure_direction_v2(x["pair_execution_id"],"B_to_A",b,a,models,p,runtime_errors);ds +=[ab,ba];cs.append(canonicalize(x["pair_execution_id"],ab,ba));prov +=[pa,pb]
 write_csv(out/"directional_measurements.csv",DIRECTIONAL_COLUMNS,ds);write_csv(out/"canonical_measurements.csv",CANONICAL_COLUMNS,cs);write_csv(out/"region_provenance.csv",["pair_execution_id","direction","region_source","target_region_source","retry_level","fallback_reason"],prov);(out/"runtime_errors.json").write_text(json.dumps(runtime_errors,indent=2));from check_local_match_results_v2 import check_results;audit=check_results(out);(out/"run_audit.json").write_text(json.dumps(audit,indent=2));return audit
def main():
 q=argparse.ArgumentParser();s=q.add_subparsers(dest="x",required=True);f=s.add_parser("freeze");f.add_argument("--output-dir",required=True);r=s.add_parser("run");r.add_argument("--package-zip",required=True);r.add_argument("--output-dir",required=True);a=q.parse_args();print(json.dumps(freeze(a.output_dir) if a.x=="freeze" else run(a.package_zip,a.output_dir),indent=2))
if __name__=="__main__":main()
