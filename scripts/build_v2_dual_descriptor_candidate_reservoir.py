#!/usr/bin/env python3
"""Build PF-ERI v2 canonical pairs and directed memberships from accepted runs."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts import build_v2_canonical_pair_contract as contract
OUT=ROOT/'outputs/pferi_v2/dual_descriptor_queue'
RUNS={'megadescriptor_l_384': ROOT/'outputs/pferi_v2/fresh_descriptor_runs/megadescriptor_l_384/pair_scores.csv','dinov2_vitl14': ROOT/'outputs/pferi_v2/fresh_descriptor_runs/dinov2_vitl14/scores.csv'}

def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def build():
    canonical={}; memberships=[]; source_counts={}
    for descriptor,path in RUNS.items():
        rows=read(path); source_counts[descriptor]=len(rows); seen=set(); ranks=Counter()
        for row in rows:
            q=row['query_image_id']; c=row['candidate_image_id']; score=row.get('cosine_similarity',row.get('descriptor_similarity'))
            rank=row.get('candidate_rank')
            if not rank: rank=str(ranks[q]+1)
            ranks[q]+=1
            if q==c or (q,c) in seen: raise ValueError(f'invalid directed membership in {descriptor}')
            seen.add((q,c)); left,right=sorted((q,c)); pair_id=contract.canonical_pair_id(left,right)
            canonical.setdefault(pair_id,{'contract_version':contract.CONTRACT_VERSION,'canonical_pair_id':pair_id,'endpoint_a_image_id':left,'endpoint_b_image_id':right,'source_dataset':'czechlynx_v2_frozen_descriptor_queue','pair_availability_status':'available','pair_inclusion_status':'eligible','exclusion_reason':''})
            memberships.append({'contract_version':contract.CONTRACT_VERSION,'canonical_pair_id':pair_id,'descriptor_name':descriptor,'queue_name':'v2_fresh_top20','queue_snapshot_id':'v2_dual_descriptor_queue_20260711','query_image_id':q,'candidate_image_id':c,'candidate_rank':rank,'descriptor_similarity':score,'membership_direction':'a_to_b' if q==left else 'b_to_a'})
    audit=contract.validate_contract(list(canonical.values()),memberships,[])
    audit.update({'source_score_rows':source_counts,'canonical_pair_count':len(canonical),'membership_count':len(memberships),'claim_boundary':'Fresh descriptor queue only; no outcome, identity truth, PF-ERI feature, or routing result.'})
    if audit['status']!='PASS':raise ValueError(audit['error_codes'])
    write(OUT/'canonical_pairs.csv',list(canonical.values()),contract.CANONICAL_PAIR_COLUMNS)
    write(OUT/'candidate_memberships.csv',memberships,contract.CANDIDATE_MEMBERSHIP_COLUMNS)
    (OUT/'dual_descriptor_queue_audit.json').write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return audit
if __name__=='__main__': print(json.dumps(build(),indent=2,sort_keys=True))
