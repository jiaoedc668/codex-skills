import copy
import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_dual_format_v6 import candidate_v6

class DeliveryV6Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("delivery_contract"),"delivery contract is not implemented")
        self.m=importlib.import_module("delivery_contract")

    def event(self,identity="c1",sid="B01",version=1,format="story"):
        return {"candidate_id":identity,"script_id":sid,"version":version,"format":format,"batch_id":"batch1","source_sha256":"a"*64,"word_sha256":"b"*64}

    def test_numbering_across_batches_and_revision(self):
        rows=[self.event()]
        self.assertEqual(("B02",1),self.m.allocate(rows,"c2","story"))
        self.assertEqual(("B01",2),self.m.allocate(rows,"c1","story"))
        self.assertEqual(("A01",1),self.m.allocate(rows,"c3","monologue"))
        rows.append(self.event("c2","B02",1))
        self.assertEqual(("B03",1),self.m.allocate(rows,"c4","story"))

    def test_duplicate_number_cannot_be_reassigned(self):
        with self.assertRaises(ValueError): self.m.validate_registry([self.event(),self.event("c2")])

    def test_revision_cannot_move_number_or_go_backwards(self):
        for row in [self.event("c1","B02",2),self.event("c1","B01",1),self.event("c1","B01",3)]:
            with self.subTest(row=row),self.assertRaises(ValueError):self.m.validate_registry([self.event(),row])

    def test_format_change_cannot_relabel_stable_identity(self):
        with self.assertRaises(ValueError):self.m.allocate([self.event()],"c1","monologue")

    def test_ordinary_confirmation_gate_and_tamper(self):
        c=candidate_v6();i=c["candidate"]
        sel={"event_type":"candidate_selection","feedback_id":"s","batch_id":i["batch_id"],"candidate_id":i["candidate_id"],"user_quote":"选这条"}
        conf={"event_type":"copy_confirmation","feedback_id":"f","batch_id":i["batch_id"],"candidate_id":i["candidate_id"],"revision_id":i["revision_id"],"content_sha256":self.m.content_hash(c),"user_quote":"确认这个版本"}
        with self.assertRaises(ValueError):self.m.ordinary_gate(c,[])
        with self.assertRaises(ValueError):self.m.ordinary_gate(c,[conf,sel])
        self.m.ordinary_gate(c,[sel,conf])
        c["script"]["lines"][0]["text"]+="改动"
        with self.assertRaises(ValueError):self.m.ordinary_gate(c,[sel,conf])

    def test_special_authority_missing_or_tampered_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); task=root/"task.txt";task.write_text("重写后直接交7个Word",encoding="utf-8")
            original=root/"生成脚本/发哥老板IP/正式交付/2026-09-06"
            (original/"资料").mkdir(parents=True)
            scopes=[]
            for n in range(1,8):
                word=original/f"{n:02d}-原稿.docx";word.write_bytes(b"test original reference")
                old_path=original/"资料"/(word.stem+"-源数据.json")
                old_path.write_text(json.dumps({"candidate":{"candidate_id":f"old{n}","revision_id":"r1"},"output_version":"V1"}),encoding="utf-8")
                scopes.append({"candidate_id":f"old{n}","script_id":f"B{n:02d}","old_source_path":str(old_path),"old_source_sha256":self.m.file_hash(old_path)})
            old=Path(scopes[0]["old_source_path"])
            c=candidate_v6();c["candidate"]["candidate_id"]="old1";c["candidate"]["revision_id"]="r2"
            envelope={"candidate_doc":c,"delivery":{"script_id":"B01","version":2},"lineage":{"source_path":str(old),"source_sha256":self.m.file_hash(old)}}
            scope={"candidate_id":"old1","script_id":"B01","old_source_path":str(old),"old_source_sha256":self.m.file_hash(old)}
            authority={"kind":"rewrite_delivery_authorization","task_path":str(task),"task_sha256":self.m.file_hash(task),"user_quote":"重写后直接交7个Word","scope":scopes,"bindings":[{"script_id":"B01","source_sha256":self.m.content_hash(envelope)}]}
            with self.assertRaises(ValueError):self.m.special_gate(envelope,None,root)
            self.m.special_gate(envelope,authority,root)
            shortened=copy.deepcopy(authority);shortened["scope"]=shortened["scope"][:1]
            with self.assertRaises(ValueError):self.m.special_gate(envelope,shortened,root)
            forged=copy.deepcopy(authority);forged["scope"][6]["candidate_id"]="unrelated"
            with self.assertRaises(ValueError):self.m.special_gate(envelope,forged,root)
            envelope["candidate_doc"]["script"]["theme"]+="修改"
            with self.assertRaises(ValueError):self.m.special_gate(envelope,authority,root)

    def test_special_authority_rejects_task_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);task=root/"task.txt";task.write_text("未授权",encoding="utf-8")
            auth={"kind":"rewrite_delivery_authorization","task_path":str(task),"task_sha256":"0"*64,"user_quote":"重写后直接交7个Word","scope":[],"bindings":[]}
            with self.assertRaises(ValueError):self.m.special_gate({},auth,root)

if __name__=="__main__":unittest.main()
