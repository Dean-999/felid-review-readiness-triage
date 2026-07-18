#!/usr/bin/env python3
"""Build an opaque, outcome-free two-annotator structural-oracle package."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEED = "pferi-v2-structural-oracle-asset-seed-001"
PACKET_COLUMNS = ["annotation_packet_id", "left_asset_token", "right_asset_token", "instrument_version", "annotation_form_schema_version"]
LINKAGE_COLUMNS = ["annotation_packet_id", "canonical_pair_id", "left_image_id", "right_image_id", "left_asset_token", "right_asset_token"]
FORBIDDEN = ("identity", "outcome", "review", "descriptor", "similarity", "rank", "route", "feature", "score", "path", "filename", "source", "canonical", "endpoint")

def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def sha(path: Path) -> str:
    d=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): d.update(b)
    return d.hexdigest()
def token(kind: str, value: str) -> str: return f"{kind}_{hashlib.sha256((SEED+':'+value).encode()).hexdigest()[:24]}"
def write_csv(path: Path, rows: list[dict[str,str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def build(pilot: list[dict[str,str]], canonical: list[dict[str,str]], execution: list[dict[str,str]], out: Path, linkage: Path, archive: Path, audit_path: Path) -> dict[str,Any]:
    if out.exists() or linkage.exists() or archive.exists(): raise FileExistsError("refusing to overwrite annotation package artifacts")
    pairs={r['canonical_pair_id'] for r in pilot if r.get('pilot_inclusion_status')=='included'}
    selected=[r for r in canonical if r.get('canonical_pair_id') in pairs]
    if len(selected)!=len(pairs): raise ValueError("pilot linkage incomplete")
    em={r['image_id']:r for r in execution}
    ids={r[k] for r in selected for k in ('endpoint_a_image_id','endpoint_b_image_id')}
    if set(ids)-set(em): raise ValueError("execution manifest lacks selected image")
    assets={i: token('asset',i) for i in ids}
    packet=[]; links=[]
    for r in sorted(selected,key=lambda x:x['canonical_pair_id']):
        pid=token('packet',r['canonical_pair_id']); left,right=r['endpoint_a_image_id'],r['endpoint_b_image_id']
        packet.append({'annotation_packet_id':pid,'left_asset_token':assets[left],'right_asset_token':assets[right],'instrument_version':'pferi_v2_structural_oracle_v1','annotation_form_schema_version':'pferi_v2_structural_oracle_form_v1'})
        links.append({'annotation_packet_id':pid,'canonical_pair_id':r['canonical_pair_id'],'left_image_id':left,'right_image_id':right,'left_asset_token':assets[left],'right_asset_token':assets[right]})
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='.oracle_') as temp:
        tmp=Path(temp)/'structural_oracle_annotation_package'; images=tmp/'images';images.mkdir(parents=True)
        write_csv(tmp/'annotation_packets.csv',packet,PACKET_COLUMNS)
        (tmp/'ANNOTATOR_INSTRUCTIONS.txt').write_text('Independently record only visible structure under structural_oracle_annotation_contract_v1. Do not judge identity or reviewability. Report technical display problems without entering structural values.\n',encoding='utf-8')
        for i in sorted(ids):
            src=(ROOT/em[i]['image_path_relative']).resolve(); dst=images/(assets[i]+src.suffix.lower())
            if not src.is_file() or sha(src)!=em[i]['content_sha256']: raise ValueError('source integrity failure')
            shutil.copyfile(src,dst)
            if sha(dst)!=em[i]['content_sha256']: raise ValueError('copy integrity failure')
        with zipfile.ZipFile(Path(temp)/archive.name,'w',compression=zipfile.ZIP_STORED) as z:
            for p in sorted(tmp.rglob('*')):
                if p.is_file(): z.write(p,p.relative_to(tmp.parent))
        with zipfile.ZipFile(Path(temp)/archive.name) as z:
            for image_id in ids:
                source_suffix = Path(em[image_id]['image_path_relative']).suffix.lower()
                member = f"structural_oracle_annotation_package/images/{assets[image_id]}{source_suffix}"
                if hashlib.sha256(z.read(member)).hexdigest() != em[image_id]['content_sha256']:
                    raise ValueError('ZIP asset integrity failure')
        shutil.move(str(tmp),out);shutil.move(str(Path(temp)/archive.name),archive)
    write_csv(linkage,links,LINKAGE_COLUMNS)
    with zipfile.ZipFile(archive) as z: names=z.namelist(); blob='\n'.join(names+[z.read('structural_oracle_annotation_package/annotation_packets.csv').decode()])
    leaks=[x for x in FORBIDDEN if x in blob.lower()]
    audit={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if not leaks else 'FAIL','pilot_pair_count':len(packet),'unique_asset_count':len(ids),'zip_member_count':len(names),'zip_sha256':sha(archive),'asset_byte_verification':'PASS','forbidden_public_token_hits':leaks,'claim_boundary':'Feature-only oracle annotation package; not a reviewability or identity task.'}
    audit_path.write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n',encoding='utf-8'); return audit
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True);p.add_argument('--canonical',type=Path,required=True);p.add_argument('--execution',type=Path,required=True);p.add_argument('--package-dir',type=Path,required=True);p.add_argument('--restricted-linkage',type=Path,required=True);p.add_argument('--zip',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);a=p.parse_args()
    audit=build(read_csv(a.pilot),read_csv(a.canonical),read_csv(a.execution),a.package_dir.resolve(),a.restricted_linkage.resolve(),a.zip.resolve(),a.audit.resolve());print(json.dumps(audit,indent=2));return 0 if audit['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
