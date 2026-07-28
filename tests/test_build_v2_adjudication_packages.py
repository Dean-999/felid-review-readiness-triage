from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from scripts import build_v2_adjudication_packages as builder
from scripts import build_v2_formal_reviewer_packages as formal


class AdjudicationPackageTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)

    def make_inputs(self, root: Path) -> dict[str, Path]:
        image_dir = root / "data/frozen/pferi_v2/lynx-wild/images"; image_dir.mkdir(parents=True)
        execution = []
        for i in range(12):
            p=image_dir/f"i{i}.jpg"; Image.new("RGB",(30+i,20+i),(i*10,40,80)).save(p)
            execution.append({"image_id":f"image_{i}","image_path_relative":f"outputs/final_freeze/lynx-wild/images/i{i}.jpg","content_sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
        codes=["rv_a","rv_b","rv_c","rv_d"]
        assignments=[]; responses={c:[] for c in codes}
        decisions=[("review_ready","not_review_ready"),("uncertain","review_ready"),("not_review_ready","uncertain"),("review_ready","not_review_ready"),("uncertain","not_review_ready"),("review_ready","review_ready")]
        for i,(d1,d2) in enumerate(decisions):
            pair=f"pair_{i}"; reviewers=(codes[i%4],codes[(i+1)%4])
            for j,code in enumerate(reviewers):
                packet=f"task_{i}_{code}"; peer=reviewers[1-j]
                assignments.append({
                    "assignment_contract_version":"pferi_v2_formal_review_instrument_contract_v1","review_packet_id":packet,"canonical_pair_id":pair,
                    "formal_sampling_stage":["development","calibration","deployment_confirmation","mechanism_confirmation"][i%4],
                    "reviewer_assignment_id":f"assign_{i}_{code}","reviewer_code":code,"peer_reviewer_code":peer,
                    "eligible_adjudicator_codes":";".join(c for c in codes if c not in reviewers),"left_image_id":f"image_{i*2}","right_image_id":f"image_{i*2+1}",
                    "left_asset_token":f"asset_{i*2:020x}","right_asset_token":f"asset_{i*2+1:020x}","packet_batch_id":"batch","assignment_status":"provisional_not_released"})
                d=decisions[i][j]; reason="none_review_ready" if d=="review_ready" else "low_evidence"
                responses[code].append({"review_packet_id":packet,"raw_reviewer_response_id":f"response_{i}_{code}","review_decision":d,"reason_codes":reason,"confidence":"medium","optional_note":"","submitted_at_utc":"2026-07-20T00:00:00Z","technical_problem_flag":"no"})
        assignment_path=root/"assignment.csv"; execution_path=root/"execution.csv"; returns=root/"returns"
        self.write_csv(assignment_path,formal.ASSIGNMENT_COLUMNS,assignments); self.write_csv(execution_path,formal.EXECUTION_COLUMNS,execution)
        for code,rows in responses.items(): self.write_csv(returns/code/"raw_responses.csv",formal.RAW_RESPONSE_COLUMNS,rows)
        disposition=root/"disposition.json"; disposition.write_text(json.dumps({"status":"PASS_HUMAN_AUTHORSHIP_ATTESTED_WITH_MAJOR_PROTOCOL_DEVIATION","adjudication_generation_authorized":True}),encoding="utf-8")
        return {"assignment":assignment_path,"execution":execution_path,"returns":returns,"disposition":disposition}

    def test_builds_only_disagreements_once_and_never_exposes_prior_answers(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); inputs=self.make_inputs(root); out=root/"out"
            audit=builder.build_adjudication_packages(assignment_path=inputs["assignment"],returns_dir=inputs["returns"],disposition_path=inputs["disposition"],execution_manifest_path=inputs["execution"],project_root=root,output_dir=out,max_zip_bytes=10_000_000)
            self.assertEqual(audit["disagreement_pair_count"],5)
            self.assertEqual(sum(audit["adjudicator_task_counts"].values()),5)
            self.assertLessEqual(max(audit["adjudicator_task_counts"].values())-min(audit["adjudicator_task_counts"].values()),1)
            tasks=[]
            for z in sorted((out/"candidate_adjudication_packages").glob("*.zip")):
                self.assertLessEqual(z.stat().st_size,10_000_000)
                with zipfile.ZipFile(z) as a:
                    names=a.namelist(); self.assertFalse(any("restricted" in n.lower() for n in names))
                    text=a.read("reviewer_view/reviewer_packet.csv").decode()
                    self.assertNotIn("canonical_pair_id",text); self.assertNotIn("reviewer_code",text)
                    rows=list(csv.DictReader(text.splitlines())); tasks += [r["review_packet_id"] for r in rows]
            self.assertEqual(len(tasks),5); self.assertEqual(len(tasks),len(set(tasks)))


if __name__ == "__main__": unittest.main()
