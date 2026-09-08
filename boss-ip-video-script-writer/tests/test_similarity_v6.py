import copy
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import check_content_similarity as similarity
from test_dual_format_v6 import candidate_v6
import delivery_contract as dc

class SimilarityV6Tests(unittest.TestCase):
    def test_new_format_same_copy_is_detected(self):
        c=candidate_v6()
        row={"event_type":"script","status":"produced","title":c["script"]["theme"],"body_text":"".join(l["text"] for l in c["script"]["lines"])}
        try:failures=similarity.find_similarity_failures(c,[row])
        except ValueError as exc:self.fail(str(exc))
        self.assertTrue(any("body similarity" in f for f in failures))

    def test_verified_revision_excludes_only_its_own_source(self):
        self.assertTrue(hasattr(similarity,"revision_history"),"verified revision history not implemented")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=candidate_v6();old["output_version"]="V1";p=root/"old.json";p.write_text(json.dumps(old),encoding="utf-8")
            new=candidate_v6();new["candidate"]["revision_id"]="r2"
            envelope={"candidate_doc":new,"delivery":{"script_id":"B01","version":2},"lineage":{"source_path":str(p),"source_sha256":dc.file_hash(p)}}
            own={"event_type":"script","status":"produced","source_json":str(p),"title":old["script"]["theme"]}
            unrelated={"event_type":"script","status":"produced","title":old["script"]["theme"]}
            self.assertEqual([unrelated],similarity.revision_history(envelope,[own,unrelated],root))
            envelope["lineage"]["source_sha256"]="0"*64
            with self.assertRaises(ValueError):similarity.revision_history(envelope,[own],root)

if __name__=="__main__":unittest.main()
