"""Human feedback projection for v6 formats, separate from historical v5 outcomes."""
from datetime import datetime
import re
from history_manager import validate_feedback_event


def derive(manifests,feedback_rows):
    normalized=[];batch_ids=set()
    for m in manifests:
        if not isinstance(m,dict) or m.get("schema_version")!=2 or m.get("format") not in {"story","monologue"}:raise ValueError("v6 manifest requires schema 2 and story/monologue format")
        if not isinstance(m.get("batch_id"),str) or not m["batch_id"] or m["batch_id"] in batch_ids:raise ValueError("unique batch_id required")
        batch_ids.add(m["batch_id"])
        at=datetime.fromisoformat(m["submitted_at"])
        if at.tzinfo is None:raise ValueError("manifest submission time must include timezone")
        candidates=m.get("candidates")
        requested=m.get("requested_candidate_count",3)
        if isinstance(requested,bool) or not isinstance(requested,int) or requested<1:raise ValueError("requested_candidate_count must be a positive integer")
        if not isinstance(candidates,list) or len(candidates)!=requested:raise ValueError("manifest candidate count must match requested_candidate_count (default 3)")
        ids=set()
        for c in candidates:
            if not isinstance(c,dict) or set(c)!={"candidate_id","revision_id"} or not isinstance(c["candidate_id"],str) or not c["candidate_id"] or c["candidate_id"] in ids or not re.fullmatch(r"r[1-9][0-9]*",str(c["revision_id"])):raise ValueError("manifest candidates require unique IDs and current revisions")
            ids.add(c["candidate_id"])
        cause=m.get("root_cause")
        if not isinstance(cause,dict) or any(not isinstance(cause.get(k),str) or not cause[k].strip() for k in ("id","hypothesis","changed_layer")) or not isinstance(cause.get("root_level_change"),bool):raise ValueError("root cause hypothesis required")
        normalized.append((at,m))
    try:rows=[validate_feedback_event(r) for r in feedback_rows]
    except SystemExit as exc:raise ValueError(str(exc)) from exc
    if len({r["feedback_id"] for r in rows})!=len(rows):raise ValueError("duplicate feedback IDs")
    results=[];latest={};last_root={};fail_count={};previous_count={}
    for _,m in sorted(normalized,key=lambda row:row[0]):
        mode=m["format"];evaluations=[]
        for candidate in m["candidates"]:
            matches=[r for r in rows if r.get("event_type")=="candidate_evaluation" and r.get("batch_id")==m["batch_id"] and r.get("candidate_id")==candidate["candidate_id"] and r.get("revision_id")==candidate["revision_id"] and r.get("format")==mode]
            if matches:evaluations.append(matches[-1]["evaluation"])
        count=evaluations.count("direct_shoot");evaluated=len(evaluations)
        result={"batch_id":m["batch_id"],"format":mode,"direct_shoot_count":count,"evaluated_candidate_count":evaluated,"state":"pending","requires_root_cause_change":False,"requires_rollback":False,"failed_same_root_cause_count":0}
        requested=m.get("requested_candidate_count",3)
        if requested!=3:
            result["requested_candidate_count"]=requested
            if evaluated==requested:result["state"]="user_reviewed_custom_batch"
        elif evaluated==3:
            root=m["root_cause"]["id"]
            if count>=2:fail_count[mode]=0;result["state"]="user_passed_batch"
            else:
                fail_count[mode]=fail_count.get(mode,0)+1 if last_root.get(mode)==root else 1
                result["state"]="rewrite_required";result["requires_root_cause_change"]=True
                if fail_count[mode]>=3:result["state"]="redesign_required"
            result["failed_same_root_cause_count"]=fail_count[mode]
            if mode in previous_count and count<previous_count[mode]:result["requires_rollback"]=True
            last_root[mode]=root;previous_count[mode]=count
        results.append(result);latest[mode]=result
    return {"schema_version":2,"batches":results,"latest_by_format":latest,"legacy_results_inherited":False}
