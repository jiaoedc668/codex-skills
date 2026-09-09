"""Prepare selected-topic writing briefs and assemble authored v6 candidates.
The author writes the actual script; this CLI preserves inputs and validates it.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from dual_format_contract import resolve_request
from content_contract import validate_candidate,build_public_candidate
from select_topics import select_topics
from history_manager import feedback_context


def prepare(pool,topic_id,format=None,topic=None,core_viewpoint=None,refined_core_viewpoint=None,direction_rationale=None):
    if pool.get("schema_version")!=6:raise ValueError("new authoring requires schema v6 topic pool")
    result=select_topics(pool)
    selected=next((row for row in result["selected"] if row["topic_id"]==topic_id),None)
    if selected is None:raise ValueError("writing topic must be in the selected set")
    request=resolve_request(format,topic,core_viewpoint)
    if refined_core_viewpoint is not None:
        if not core_viewpoint or not isinstance(refined_core_viewpoint,str) or not refined_core_viewpoint.strip() or not isinstance(direction_rationale,str) or not direction_rationale.strip():raise ValueError("refined viewpoint requires original direction and an explicit rationale")
    elif direction_rationale is not None:raise ValueError("rationale requires a refined viewpoint")
    decision={"pool_id":result["pool_id"],"topic_id":topic_id,"priority_category":selected["priority_category"],**selected["production_case"]}
    viral_samples=deepcopy(result["viral_expression_samples"])
    evidence=deepcopy(selected["research_evidence"]);evidence["topic_kind"]=selected["topic_kind"]
    evidence["viral_expression_samples"]=deepcopy(viral_samples)
    authoring_requirements=(
        {
            "theme_scope":"life_principle",
            "incident_role":"supporting_evidence_only",
            "opening":"strong_judgment_or_suspense",
            "reason_count":{"min":2,"max":4},
            "counterargument_required":True,
            "memorable_close_required":True,
        }
        if request["format"]=="monologue"
        else {
            "theme_scope":"concrete_conflict",
            "incident_role":"primary_story",
            "opening":"event_in_progress",
            "counterargument_required":True,
        }
    )
    return {"schema_version":1,"kind":"boss_ip_writing_brief","request":request,
            "resolved_topic":topic or selected["title"],
            "resolved_core_viewpoint":refined_core_viewpoint or core_viewpoint or decision["fage_choice"],
            "direction_rationale":direction_rationale,
            "topic_decision":decision,"research_evidence":evidence,
            "viral_expression_samples":viral_samples,
            "authoring_requirements":authoring_requirements,
            "writing_instruction":"仅发哥；主题是人生原则，小事只作论据；首句强判断或悬念，2至4个不重复理由，回应现实反驳，以前文托得住的走心判断收尾，约30秒尽量45秒内。" if request["format"]=="monologue" else "朋友或同事讲自己的事，发哥只追问分析建议，当事人决定，约60秒尽量90秒内。",
            "boundary":"发哥不得参与、介绍、安排或代办；对白、动作、镜头、前史全部审读。"}


def assemble(brief,authored,persona,feedback_rows):
    if brief.get("kind")!="boss_ip_writing_brief" or brief.get("schema_version")!=1:raise ValueError("invalid writing brief")
    result=deepcopy(authored)
    if result.get("format")!=brief["request"]["format"]:raise ValueError("authored format differs from requested format")
    if result.get("script",{}).get("core_viewpoint")!=brief["resolved_core_viewpoint"]:raise ValueError("authored viewpoint differs from recorded direction; document refinement before writing")
    result["request"]=deepcopy(brief["request"])
    if brief["request"]["topic"] is not None:
        alignment=authored.get("request",{}).get("topic_alignment")
        if not isinstance(alignment,dict) or alignment.get("requested_topic")!=brief["resolved_topic"]:
            raise ValueError("specified topic requires authored topic alignment with script evidence")
        result["request"]["topic_alignment"]=deepcopy(alignment)
    result["research_evidence"]=deepcopy(brief["research_evidence"])
    result["topic_decision"]=deepcopy(brief["topic_decision"])
    result["feedback_context"]=feedback_context(feedback_rows)
    check=validate_candidate(result,persona,feedback_rows)
    if check.failures:raise ValueError("; ".join(check.failures))
    return result


def load(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    prep=sub.add_parser("prepare")
    prep.add_argument("--topic-pool",type=Path,required=True);prep.add_argument("--topic-id",required=True)
    prep.add_argument("--format",choices=["story","monologue"]);prep.add_argument("--topic");prep.add_argument("--core-viewpoint")
    prep.add_argument("--refined-core-viewpoint");prep.add_argument("--direction-rationale")
    build=sub.add_parser("assemble")
    build.add_argument("--brief",type=Path,required=True);build.add_argument("--input",type=Path,required=True)
    build.add_argument("--persona",type=Path,required=True);build.add_argument("--feedback-ledger",type=Path,required=True)
    public=sub.add_parser("public");public.add_argument("--input",type=Path,required=True)
    for command in (prep,build,public):command.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="prepare":result=prepare(load(args.topic_pool),args.topic_id,args.format,args.topic,args.core_viewpoint,args.refined_core_viewpoint,args.direction_rationale)
        elif args.command=="assemble":
            rows=[json.loads(line) for line in args.feedback_ledger.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
            result=assemble(load(args.brief),load(args.input),load(args.persona),rows)
        else:result=build_public_candidate(load(args.input))
        with args.output.open("x",encoding="utf-8") as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        print("INTEGRITY PASS: "+str(args.output))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("INTEGRITY FAIL: "+str(exc));return 2

if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
