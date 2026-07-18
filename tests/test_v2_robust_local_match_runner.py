from __future__ import annotations
import sys, unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"gpu/kaggle_v2_local_matcher_v2"))
import local_match_runner_v2 as runner

class RobustRegionTests(unittest.TestCase):
 def test_parse_matcher_output_supports_tensor_dict_list_and_tuple(self):
   class FakeTensor:
    def __init__(self,a): self.a=a
    def detach(self): return self
    def cpu(self): return self
    def numpy(self): return self.a
   value=FakeTensor(np.array([[0,1],[2,3]]))
   self.assertEqual(runner.parse_matcher_output(value,tensor_type=FakeTensor).shape,(2,2))
   self.assertEqual(runner.parse_matcher_output({"matches0":FakeTensor(np.array([[1,-1,0]]))},tensor_type=FakeTensor).shape,(2,2))
   self.assertEqual(runner.parse_matcher_output([({"wrapper":[{"matches":value}]},)],tensor_type=FakeTensor).shape,(2,2))
   self.assertEqual(runner.parse_matcher_output(({"matches01":value},),tensor_type=FakeTensor).shape,(2,2))
 def test_parse_matcher_output_reports_unsupported_shape(self):
  with self.assertRaisesRegex(RuntimeError,"keys"):
   runner.parse_matcher_output({"unexpected":object()},tensor_type=type(None))
 def test_detector_mask_wins(self):
  img=np.zeros((20,20,3),np.uint8); detector=np.zeros((20,20),bool); detector[2:8,2:8]=True
  _,source,_=runner.select_region(img,detector,runner.DEFAULT_PARAMETERS); self.assertEqual(source,"detector")
 def test_fallback_and_full_image_are_nonfailing(self):
  fg=np.zeros((50,50,3),np.uint8); fg[20:40,20:40]=255
  _,source,_=runner.select_region(fg,None,runner.DEFAULT_PARAMETERS); self.assertEqual(source,"fallback_bbox")
  _,source,_=runner.select_region(np.zeros((50,50,3),np.uint8),None,runner.DEFAULT_PARAMETERS); self.assertEqual(source,"full_image")
 def test_canonical_failure_is_not_zero(self):
  row=runner.canonicalize("p",runner.valid_row("A_to_B",.3),runner.failed_row("B_to_A","model_runtime_error"))
  self.assertEqual(row["local_match_coverage_fraction"],"")

if __name__=="__main__": unittest.main()
