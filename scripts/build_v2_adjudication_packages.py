#!/usr/bin/env python3
"""Build blinded third-person adjudication candidate packages for exact first-pass disagreements."""

from __future__ import annotations

import argparse, csv, hashlib, json, os, shutil, sys, tempfile, zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts import build_v2_formal_reviewer_packages as formal

ADJUDICATORS=["adjudicator_A","adjudicator_B","adjudicator_C","adjudicator_D"]
LINKAGE_COLUMNS=["adjudication_packet_id","canonical_pair_id","left_image_id","right_image_id","adjudicator_alias","formal_sampling_stage","first_pass_reviewer_codes","first_pass_packet_ids"]
MAX_ZIP_BYTES=500_000_000

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def read_csv(path:Path,fields:list[str])->list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f:
        r=csv.DictReader(f)
        if list(r.fieldnames or [])!=fields: raise ValueError(f"schema mismatch: {path}")
        return list(r)

def write_csv(path:Path,fields:list[str],rows:list[dict[str,Any]])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise"); w.writeheader(); w.writerows(rows)

def opaque(prefix:str,*values:str)->str:
    return prefix+hashlib.sha256("|".join(values).encode()).hexdigest()[:24]

def opaque_asset(*values:str)->str:
    return "asset_"+hashlib.sha256("|".join(values).encode()).hexdigest()[:20]

def zip_tree(root:Path,target:Path)->None:
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file(): z.write(p,p.relative_to(root))

def collect_responses(returns_dir:Path,assignment_by_packet:dict[str,dict[str,str]])->dict[str,dict[str,str]]:
    out={}
    for p in sorted(returns_dir.rglob("raw_responses.csv")):
        for row in read_csv(p,formal.RAW_RESPONSE_COLUMNS):
            packet=row["review_packet_id"]
            if packet not in assignment_by_packet: raise ValueError(f"unassigned response packet: {packet}")
            if packet in out: raise ValueError(f"duplicate response packet: {packet}")
            if row["technical_problem_flag"]!="no" or row["review_decision"] not in {"review_ready","not_review_ready","uncertain"}: raise ValueError(f"unresolved first-pass response: {packet}")
            out[packet]=row
    if set(out)!=set(assignment_by_packet): raise ValueError("returns do not exactly cover assignments")
    return out

def assign_balanced(disagreements:list[dict[str,Any]])->dict[str,str]:
    total=Counter(); stage=defaultdict(Counter); result={}
    ordered=sorted(disagreements,key=lambda x:hashlib.sha256(("adjudication_v1|"+x["canonical_pair_id"]).encode()).hexdigest())
    for row in ordered:
        s=row["formal_sampling_stage"]
        chosen=min(ADJUDICATORS,key=lambda a:(stage[s][a],total[a],a))
        result[row["canonical_pair_id"]]=chosen; stage[s][chosen]+=1; total[chosen]+=1
    return result

def build_adjudication_packages(*,assignment_path:Path,returns_dir:Path,disposition_path:Path,execution_manifest_path:Path,project_root:Path,output_dir:Path,max_zip_bytes:int=MAX_ZIP_BYTES)->dict[str,Any]:
    if output_dir.exists(): raise FileExistsError(f"refusing to overwrite: {output_dir}")
    disposition=json.loads(disposition_path.read_text(encoding="utf-8"))
    if disposition.get("adjudication_generation_authorized") is not True: raise ValueError("disposition does not authorize adjudication generation")
    assignments=read_csv(assignment_path,formal.ASSIGNMENT_COLUMNS)
    bypacket={r["review_packet_id"]:r for r in assignments}
    if len(bypacket)!=len(assignments): raise ValueError("duplicate assignment packet")
    responses=collect_responses(returns_dir,bypacket)
    pairs=defaultdict(list)
    for a in assignments: pairs[a["canonical_pair_id"]].append((a,responses[a["review_packet_id"]]))
    if any(len(v)!=2 for v in pairs.values()): raise ValueError("every pair must have exactly two first-pass responses")
    disagreements=[]
    for pair_id,entries in pairs.items():
        if entries[0][1]["review_decision"]!=entries[1][1]["review_decision"]:
            a0=entries[0][0]
            disagreements.append({"canonical_pair_id":pair_id,"formal_sampling_stage":a0["formal_sampling_stage"],"left_image_id":a0["left_image_id"],"right_image_id":a0["right_image_id"],"reviewer_codes":";".join(sorted(e[0]["reviewer_code"] for e in entries)),"packet_ids":";".join(sorted(e[0]["review_packet_id"] for e in entries))})
    allocation=assign_balanced(disagreements)
    execution=read_csv(execution_manifest_path,formal.EXECUTION_COLUMNS); ex={r["image_id"]:r for r in execution}
    required={r[k] for r in disagreements for k in ("left_image_id","right_image_id")}
    if not required.issubset(ex): raise ValueError("execution manifest missing adjudication image")
    sources={}
    for image_id in sorted(required):
        p,resolution=formal.resolve_source(project_root,ex[image_id]["image_path_relative"])
        if sha256_file(p)!=ex[image_id]["content_sha256"]: raise ValueError(f"source image hash mismatch: {image_id}")
        sources[image_id]=(p,resolution)
    staging=Path(tempfile.mkdtemp(prefix=output_dir.name+".staging.",dir=output_dir.parent if output_dir.parent.exists() else project_root))
    try:
        grouped=defaultdict(list); linkage=[]; package_info={}
        for d in disagreements: grouped[allocation[d["canonical_pair_id"]]].append(d)
        for alias in ADJUDICATORS:
            root=staging/"candidate_adjudication_packages_unzipped"/alias; view=root/"reviewer_view"; assets=view/"assets"
            public=[]; tokens={}
            for d in sorted(grouped[alias],key=lambda x:opaque("adj_",x["canonical_pair_id"])):
                packet=opaque("adjudication_task_",alias,d["canonical_pair_id"])
                lt=opaque_asset("adjudication_v1",alias,d["left_image_id"]); rt=opaque_asset("adjudication_v1",alias,d["right_image_id"])
                public.append({"review_packet_id":packet,"left_asset_token":lt,"right_asset_token":rt,"instrument_version":formal.INSTRUMENT_VERSION,"review_form_schema_version":formal.FORM_SCHEMA_VERSION})
                tokens[lt]=d["left_image_id"]; tokens[rt]=d["right_image_id"]
                linkage.append({"adjudication_packet_id":packet,"canonical_pair_id":d["canonical_pair_id"],"left_image_id":d["left_image_id"],"right_image_id":d["right_image_id"],"adjudicator_alias":alias,"formal_sampling_stage":d["formal_sampling_stage"],"first_pass_reviewer_codes":d["reviewer_codes"],"first_pass_packet_ids":d["packet_ids"]})
            for token,image_id in sorted(tokens.items()): formal.render_asset(sources[image_id][0],assets/(token+".png"))
            write_csv(view/"reviewer_packet.csv",formal.PUBLIC_PACKET_COLUMNS,public); write_csv(view/"raw_response_template.csv",formal.RAW_RESPONSE_COLUMNS,[])
            (view/"app.py").write_text(formal.APP_SOURCE,encoding="utf-8")
            (root/"README.md").write_text("# Blinded third-person pair review\n\nJudge only whether the two images contain enough comparable visible evidence for responsible individual-level review. You are making a fresh judgement. You will not see and must not seek the first-pass answers.\n\nRun: `python -m pip install -r requirements.txt` then `python -m streamlit run reviewer_view/app.py`. Return only `responses/raw_responses.csv`.\n",encoding="utf-8")
            (root/"requirements.txt").write_text("streamlit>=1.36,<2\n",encoding="utf-8")
            errors=formal.static_validate_public_view(view,len(public))
            if errors: raise RuntimeError(f"public audit failed for {alias}: {errors}")
            z=staging/"candidate_adjudication_packages"/f"PAIR_REVIEW_{alias}.zip"; zip_tree(root,z)
            if z.stat().st_size>max_zip_bytes: raise RuntimeError(f"adjudication ZIP exceeds limit: {z.name}")
            with zipfile.ZipFile(z) as arc:
                names=arc.namelist()
                if any("restricted" in n.lower() or n.startswith("/") or ".." in Path(n).parts for n in names): raise RuntimeError("unsafe or restricted ZIP member")
            package_info[alias]={"task_count":len(public),"unique_asset_count":len(tokens),"zip_size_bytes":z.stat().st_size,"zip_sha256":sha256_file(z),"static_status":"PASS"}
        write_csv(staging/"restricted"/"restricted_adjudication_linkage.csv",LINKAGE_COLUMNS,linkage)
        write_csv(staging/"restricted"/"new_adjudicator_roster_template.csv",["adjudicator_alias","restricted_person_name","training_confirmed","conflict_attestation","signed_at_utc"],[{"adjudicator_alias":a,"restricted_person_name":"","training_confirmed":"no","conflict_attestation":"pending","signed_at_utc":""} for a in ADJUDICATORS])
        (staging/"ADJUDICATOR_GUIDE_zh.md").write_text("# 第三人盲法裁决说明\n\n你需要对每个图片对作出全新的 reviewability 判断，不判断是否同一个体。你不会看到前两人的答案，也不得询问、讨论或推断。technical problem 不是语义标签。完成后只返还 `responses/raw_responses.csv`。\n",encoding="utf-8")
        counts={a:package_info[a]["task_count"] for a in ADJUDICATORS}
        audit={"built_at_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS_CANDIDATE_NOT_RELEASED","packet_release_authorized":False,"outcome_collection_authorized":False,"first_pass_pair_count":len(pairs),"disagreement_pair_count":len(disagreements),"adjudicator_task_counts":counts,"balanced_load_max_minus_min":max(counts.values())-min(counts.values()),"packages":package_info,"prior_response_values_in_public_packages":0,"source_disposition_sha256":sha256_file(disposition_path),"claim_boundary":"Candidate blinded adjudication packages only. Bind four new people, confirm training/conflicts, and pass release checks before distribution."}
        (staging/"adjudication_candidate_audit.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        lines=[f"{sha256_file(p)}  {p.relative_to(staging)}" for p in sorted(staging.rglob("*")) if p.is_file() and p.name!="CHECKSUMS.sha256"]
        (staging/"CHECKSUMS.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8")
        output_dir.parent.mkdir(parents=True,exist_ok=True); os.replace(staging,output_dir); return audit
    except Exception:
        shutil.rmtree(staging,ignore_errors=True); raise

def main(argv=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--assignment",type=Path,required=True); p.add_argument("--returns-dir",type=Path,required=True); p.add_argument("--disposition",type=Path,required=True); p.add_argument("--execution-manifest",type=Path,required=True); p.add_argument("--project-root",type=Path,default=ROOT); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--max-zip-bytes",type=int,default=MAX_ZIP_BYTES); a=p.parse_args(argv)
    audit=build_adjudication_packages(assignment_path=a.assignment,returns_dir=a.returns_dir,disposition_path=a.disposition,execution_manifest_path=a.execution_manifest,project_root=a.project_root,output_dir=a.output_dir,max_zip_bytes=a.max_zip_bytes); print(json.dumps(audit,indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
