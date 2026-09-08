"""Traceable numbering and separate ordinary/special delivery gates."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import history_manager


def content_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def resolve(root,path):
    p=Path(path)
    return p.resolve() if p.is_absolute() else (Path(root)/p).resolve()


def validate_registry(rows):
    if not isinstance(rows,list): raise ValueError("registry must be an event array")
    owners={}; identities={}; versions={}
    for row in rows:
        if not isinstance(row,dict): raise ValueError("registry event must be object")
        sid=row.get("script_id");identity=row.get("candidate_id");mode=row.get("format");version=row.get("version")
        prefix={"story":"B","monologue":"A"}.get(mode)
        if not prefix or not isinstance(sid,str) or not re.fullmatch(prefix+r"(?:0[1-9]|[1-9][0-9]+)",sid): raise ValueError("invalid registry script_id or format")
        if not isinstance(identity,str) or not identity.strip(): raise ValueError("invalid registry candidate_id")
        if not isinstance(version,int) or isinstance(version,bool) or version<1: raise ValueError("invalid registry version")
        if sid in owners and owners[sid]!=identity: raise ValueError("duplicate number assigned to another candidate")
        if identity in identities and identities[identity]!=sid: raise ValueError("same candidate cannot change number or format")
        if version!=versions.get(identity,0)+1: raise ValueError("revision versions must increase consecutively")
        if identity not in identities:
            previous=[int(s[1:]) for s in owners if s.startswith(prefix)]
            if int(sid[1:])!=max(previous,default=0)+1: raise ValueError("new numbers must increase without reuse or gaps")
        for key in ("source_sha256","word_sha256"):
            if not isinstance(row.get(key),str) or not re.fullmatch(r"[a-f0-9]{64}",row[key]):raise ValueError("registry hash missing: "+key)
        if not isinstance(row.get("batch_id"),str) or not row["batch_id"].strip():raise ValueError("registry batch_id missing")
        owners[sid]=identity;identities[identity]=sid;versions[identity]=version
    return rows


def allocate(rows,candidate_id,format):
    validate_registry(rows)
    prefix={"story":"B","monologue":"A"}.get(format)
    if not prefix:raise ValueError("unknown format")
    previous=[r for r in rows if r["candidate_id"]==candidate_id]
    if previous:
        last=previous[-1]
        if last["format"]!=format:raise ValueError("stable identity cannot change format")
        return last["script_id"],last["version"]+1
    number=max((int(r["script_id"][1:]) for r in rows if r["format"]==format),default=0)+1
    return f"{prefix}{number:02d}",1


def ordinary_gate(candidate,rows):
    identity=candidate["candidate"]
    try: validated=[history_manager.validate_feedback_event(r) for r in rows]
    except SystemExit as exc:raise ValueError(str(exc)) from exc
    selection=None
    for index,row in enumerate(validated):
        if row.get("candidate_id")!=identity["candidate_id"] or row.get("batch_id")!=identity["batch_id"]:continue
        if row.get("event_type")=="candidate_selection":selection=index
        if selection is not None and index>selection and row.get("event_type")=="copy_confirmation" and row.get("revision_id")==identity["revision_id"] and row.get("content_sha256")==content_hash(candidate):return
    raise ValueError("ordinary Word gate requires selection followed by current revision content confirmation")


def verify_lineage(envelope,root):
    lineage=envelope.get("lineage")
    if not isinstance(lineage,dict):raise ValueError("revision lineage is required")
    path=resolve(root,lineage["source_path"])
    if file_hash(path)!=lineage.get("source_sha256"):raise ValueError("old source hash mismatch")
    old=load(path)
    old_candidate=old.get("candidate_doc",old)
    current=envelope["candidate_doc"]
    if old_candidate["candidate"]["candidate_id"]!=current["candidate"]["candidate_id"]:raise ValueError("lineage candidate identity differs")
    def rev(value):
        if not isinstance(value,str) or not re.fullmatch(r"r[1-9][0-9]*",value):raise ValueError("revision ID must use rN")
        return int(value[1:])
    if rev(current["candidate"]["revision_id"])!=rev(old_candidate["candidate"]["revision_id"])+1:raise ValueError("source revision must increase by one")
    if "delivery" in old: old_version=old["delivery"]["version"]
    else:
        value=old.get("output_version")
        if not isinstance(value,str) or not re.fullmatch(r"V[1-9][0-9]*",value):raise ValueError("old source lacks output version")
        old_version=int(value[1:])
    if envelope["delivery"]["version"]!=old_version+1:raise ValueError("delivery version must increment old source version")
    return old


def original_delivery_scope(root):
    directory=Path(root)/"生成脚本/发哥老板IP/正式交付/2026-09-06"
    words=sorted(directory.glob("*.docx"))
    if len(words)!=7:raise ValueError("special authorization requires exactly seven original deliveries")
    scope=[]
    for index,word in enumerate(words,1):
        if not word.name.startswith(f"{index:02d}-"):raise ValueError("original numbering differs from 01-07")
        source=directory/"资料"/(word.stem+"-源数据.json")
        data=load(source)
        scope.append({"candidate_id":data["candidate"]["candidate_id"],"script_id":f"B{index:02d}","old_source_path":str(source.resolve()),"old_source_sha256":file_hash(source)})
    return scope


def special_gate(envelope,authority,root):
    if not isinstance(authority,dict) or authority.get("kind")!="rewrite_delivery_authorization":raise ValueError("special rewrite authorization missing")
    task=resolve(root,authority["task_path"])
    if file_hash(task)!=authority.get("task_sha256"):raise ValueError("authorization task hash mismatch")
    quote=authority.get("user_quote")
    if not isinstance(quote,str) or quote!="重写后直接交7个Word" or quote not in task.read_text(encoding="utf-8-sig"):raise ValueError("special authorization quote not found in task")
    identity=envelope["candidate_doc"]["candidate"]["candidate_id"]
    sid=envelope["delivery"]["script_id"]
    scope=authority.get("scope")
    if not isinstance(scope,list):raise ValueError("authorization scope missing")
    ids=[r.get("candidate_id") for r in scope];numbers=[r.get("script_id") for r in scope]
    if len(set(ids))!=len(ids) or len(set(numbers))!=len(numbers):raise ValueError("authorization scope duplicate identity/number")
    expected=original_delivery_scope(root)
    normalized=[]
    for row in scope:
        normalized.append({"candidate_id":row.get("candidate_id"),"script_id":row.get("script_id"),"old_source_path":str(resolve(root,row.get("old_source_path",""))),"old_source_sha256":row.get("old_source_sha256")})
    if sorted(normalized,key=lambda r:str(r["script_id"]))!=expected:
        raise ValueError("special scope must match all seven fixed original identities and hashes")
    matches=[r for r in scope if r.get("candidate_id")==identity and r.get("script_id")==sid]
    if len(matches)!=1:raise ValueError("candidate outside special authorization scope")
    entry=matches[0]
    old_path=resolve(root,entry["old_source_path"])
    if file_hash(old_path)!=entry.get("old_source_sha256"):raise ValueError("authorized old source changed")
    lineage=envelope.get("lineage",{})
    if resolve(root,lineage.get("source_path",""))!=old_path or lineage.get("source_sha256")!=entry["old_source_sha256"]:raise ValueError("lineage differs from authorized source")
    verify_lineage(envelope,root)
    if envelope["candidate_doc"].get("format")!="story" or not re.fullmatch(r"B0[1-7]",sid):raise ValueError("special scope is B01-B07 stories only")
    bindings=authority.get("bindings",[])
    found=[b for b in bindings if b.get("script_id")==sid]
    if len(found)!=1 or found[0].get("source_sha256")!=content_hash(envelope):raise ValueError("new source hash not authorized or was modified")


def validate_production(envelope):
    from dual_format_contract import boundary_failures
    if set(envelope)!={"document_kind","schema_version","candidate_doc","production_package","delivery","lineage"} or envelope.get("document_kind")!="boss_ip_delivery" or envelope.get("schema_version")!=1:raise ValueError("invalid delivery envelope")
    c=envelope["candidate_doc"];pack=envelope["production_package"]
    if not isinstance(pack,dict) or set(pack)!={"scene","cast","props","storyboard","subtitles"}:raise ValueError("production package keys differ")
    if not isinstance(pack["scene"],str) or not pack["scene"].strip():raise ValueError("scene required")
    if not isinstance(pack["cast"],list) or not pack["cast"]:raise ValueError("cast required")
    speakers={l["speaker"] for l in c["script"]["lines"]}
    roles=set()
    for row in pack["cast"]:
        if not isinstance(row,dict) or set(row)!={"role","visibility"} or any(not isinstance(v,str) or not v.strip() for v in row.values()):raise ValueError("invalid cast")
        roles.add(row["role"])
    if roles!=speakers or len(roles)!=len(pack["cast"]):raise ValueError("cast differs from dialogue speakers")
    if not isinstance(pack["props"],list) or any(not isinstance(x,str) or not x.strip() for x in pack["props"]):raise ValueError("props must be text array")
    ids=[l["line_id"] for l in c["script"]["lines"]]
    if not isinstance(pack["storyboard"],list) or not pack["storyboard"]:raise ValueError("storyboard required")
    covered=[]
    for shot in pack["storyboard"]:
        if not isinstance(shot,dict) or set(shot)!={"line_ids","action","shot"}:raise ValueError("storyboard keys differ")
        if not isinstance(shot["line_ids"],list) or not shot["line_ids"]:raise ValueError("storyboard line_ids required")
        for key in ("action","shot"):
            if not isinstance(shot[key],str) or not shot[key].strip():raise ValueError("storyboard text required")
        covered.extend(shot["line_ids"])
    if covered!=ids:raise ValueError("storyboard must cover each line in order exactly once")
    if pack["subtitles"]!="完整对白逐句同步，按自然停顿分行。":raise ValueError("subtitles must cover complete dialogue")
    failures=boundary_failures(pack)
    if failures:raise ValueError("; ".join(failures))
    delivery=envelope["delivery"]
    if not isinstance(delivery,dict) or set(delivery)!={"script_id","version"}:raise ValueError("delivery identity required")
    prefix="B" if c["format"]=="story" else "A"
    if not isinstance(delivery["script_id"],str) or not re.fullmatch(prefix+r"(?:0[1-9]|[1-9][0-9]+)",delivery["script_id"]):raise ValueError("delivery number does not match format")
    if not isinstance(delivery["version"],int) or isinstance(delivery["version"],bool) or delivery["version"]<1:raise ValueError("delivery version required")


def authored_feedback_prefix(candidate, rows):
    """Validate the actual pre-confirmation feedback snapshot without rewriting copy."""
    target = candidate.get("feedback_context")
    if not isinstance(target, dict):
        raise ValueError("authored feedback snapshot missing")
    ids = target.get("latest_feedback_ids")
    if not isinstance(ids, list):
        raise ValueError("authored feedback IDs must be a list")
    all_ids = [row.get("feedback_id") for row in rows]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("duplicate feedback IDs")
    if ids:
        if ids[-1] not in all_ids:
            raise ValueError("authored feedback snapshot not present in ledger")
        prefix = rows[:all_ids.index(ids[-1]) + 1]
    else:
        prefix = []
    if history_manager.feedback_context(prefix) != target:
        raise ValueError("authored feedback snapshot does not match a real ledger prefix")
    return prefix
