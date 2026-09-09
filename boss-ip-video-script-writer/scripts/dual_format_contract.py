"""Schema v6 separates advisory stories from single-speaker commentary.
Structural checks are not semantic approval. Review all spoken and visual text.
"""
from __future__ import annotations
from collections.abc import Mapping
import re
from copy import deepcopy
import history_manager
import select_topics

FORMATS = {"story": ("剧情", "约60秒剧情"), "monologue": ("口播", "约30秒口播")}
TOP_KEYS = {"schema_version", "candidate", "format", "request", "research_evidence", "topic_decision", "persona_continuity", "feedback_context", "creative_blueprint", "script"}
BLUEPRINT_KEYS = {"situation", "stakeholder", "grievance", "choice_and_consequence", "counterargument", "judgment", "next_step", "opening_claim", "reason", "example"}
SCRIPT_REQUIRED_KEYS = {"theme", "core_viewpoint", "lines", "key_actions", "necessary_shots", "backstory", "ending"}
SCRIPT_KEYS = SCRIPT_REQUIRED_KEYS | {"title"}
ACTS = {"tell", "ask", "judge", "advise", "object", "decide", "explain"}
# Deliberately conservative detection of explicit intervention, not a semantic oracle.
INTERVENTION = re.compile(r"(?:我|发哥)(?:已经|刚|来|会|再|亲自|负责|替你|帮你|替朋友|帮朋友|替他|帮他|给你|替她|帮她){0,4}(?:联系|介绍|安排|代办|催债|签假|批假|调班|招聘|借钱|垫钱|打电话|签字|陪你去|接孩子|留工位|留工作)")
NARRATED = re.compile(r"发哥[^。！？\n]{0,10}(?:替|帮|负责)[^。！？\n]{0,12}(?:联系|介绍|安排|催|借|招|调班|签|接孩子)")


def resolve_request(format=None, topic=None, core_viewpoint=None):
    mode = format or "story"
    if mode not in FORMATS:
        raise ValueError("format must be story or monologue")
    for key,value in (("topic",topic),("core_viewpoint",core_viewpoint)):
        if value is not None and (not isinstance(value,str) or not value.strip()):
            raise ValueError(key + " must be non-empty text when supplied")
    return {"format":mode,"topic":topic,"core_viewpoint":core_viewpoint}


def public_candidate(data):
    script=data["script"]
    return {
        "subject": script["theme"],
        "title": script.get("title", script["theme"]),
        "full_copy": [
            {"speaker": line["speaker"], "text": line["text"]}
            for line in script["lines"]
        ],
    }


def boundary_failures(script):
    import content_contract as legacy
    failures=[]
    lines=script.get("lines",[])
    if isinstance(lines,list):
        for line in lines:
            if isinstance(line,Mapping) and line.get("speaker")=="发哥" and INTERVENTION.search(str(line.get("text",""))):
                failures.append("persona boundary: explicit Fage intervention in " + str(line.get("line_id")))
    for text in legacy._all_text(script):
        if NARRATED.search(text): failures.append("persona boundary: narrated Fage intervention")
    return failures


def validate_candidate(data, persona, feedback_rows):
    import content_contract as legacy
    failures=[]
    if not isinstance(data,Mapping): return legacy.IntegrityResult(["candidate must be an object"])
    if set(data)!=TOP_KEYS: failures.append("v6 top-level keys differ from contract")
    if data.get("schema_version")!=6: failures.append("schema_version must be 6")
    mode=data.get("format")
    if mode not in FORMATS: failures.append("format must be story or monologue")
    def obj(key):
        value=data.get(key)
        if not isinstance(value,Mapping): failures.append(key+" must be an object");return {}
        return value
    identity=obj("candidate");legacy._validate_candidate_identity(identity,failures)
    request=obj("request")
    try:
        if set(request)-{"topic_alignment"}!={"format","topic","core_viewpoint"}: raise ValueError("request keys differ from contract")
        resolved=resolve_request(**{k:request[k] for k in ("format","topic","core_viewpoint")})
        if resolved["format"]!=mode: failures.append("request format differs from candidate format")
    except (TypeError,ValueError) as exc: failures.append(str(exc))
    research_evidence=obj("research_evidence")
    legacy._validate_research_evidence(research_evidence,failures)
    try:
        select_topics.validate_viral_expression_samples(
            research_evidence.get("viral_expression_samples")
        )
    except ValueError as exc:
        failures.append("viral expression research invalid: "+str(exc))
    topic=obj("topic_decision")
    expected=(legacy.TOPIC_DECISION_KEYS-{"fage_cost"})|{"stakeholder_cost"}
    if set(topic)!=expected: failures.append("v6 topic_decision keys differ from contract")
    for key in expected: legacy._require_text(topic,key,"topic_decision."+key,failures)
    if not isinstance(persona,Mapping): failures.append("persona must be an object")
    else:
        failures.extend(legacy.validate_persona_model(persona))
        legacy._validate_persona_reference(obj("persona_continuity"),persona,failures)
    if dict(obj("feedback_context"))!=history_manager.feedback_context(feedback_rows): failures.append("feedback_context differs from current explicit ledger")
    blueprint=obj("creative_blueprint")
    if set(blueprint)!=BLUEPRINT_KEYS: failures.append("creative_blueprint keys differ from contract")
    required=BLUEPRINT_KEYS-{"opening_claim"} if mode=="story" else BLUEPRINT_KEYS-{"stakeholder","grievance","choice_and_consequence"}
    for key in required: legacy._require_text(blueprint,key,"creative_blueprint."+key,failures)
    if mode=="story" and blueprint.get("stakeholder")=="发哥": failures.append("persona boundary: Fage cannot be stakeholder")
    script=obj("script")
    if not SCRIPT_REQUIRED_KEYS.issubset(script) or set(script)-SCRIPT_KEYS:
        failures.append("v6 script keys differ from contract")
    for key in ("theme","core_viewpoint","backstory"): legacy._require_text(script,key,"script."+key,failures)
    if "title" in script:
        legacy._require_text(script,"title","script.title",failures)
    if blueprint.get("judgment")!=script.get("core_viewpoint"): failures.append("judgment must match core_viewpoint")
    lines=script.get("lines")
    if not isinstance(lines,list) or not lines: failures.append("lines must be non-empty");lines=[]
    ids=[];speakers=[]
    for line in lines:
        if not isinstance(line,Mapping): failures.append("line must be object");continue
        if set(line)!={"line_id","speaker","text","dialogue_act"}: failures.append("line keys differ from contract")
        for key in ("line_id","speaker","text"): legacy._require_text(line,key,"line."+key,failures)
        ids.append(line.get("line_id"));speakers.append(line.get("speaker"))
        if line.get("dialogue_act") not in ACTS: failures.append("invalid dialogue_act")
    if ids != [f"L{i}" for i in range(1,len(lines)+1)]: failures.append("line IDs must be sequential unique L1..Ln")
    if request.get("topic") is not None:
        alignment=request.get("topic_alignment")
        if not isinstance(alignment,Mapping) or set(alignment)!={"requested_topic","script_excerpt","explanation"}:
            failures.append("specified topic requires traceable topic_alignment")
        elif alignment.get("requested_topic")!=request["topic"] or not isinstance(alignment.get("script_excerpt"),str) or not alignment["script_excerpt"].strip() or alignment["script_excerpt"] not in "".join(str(l.get("text","")) for l in lines if isinstance(l,Mapping)) or not isinstance(alignment.get("explanation"),str) or not alignment["explanation"].strip():
            failures.append("topic_alignment must bind requested topic to actual script evidence and explanation")
    if mode=="monologue":
        if any(s!="发哥" for s in speakers): failures.append("monologue requires single speaker Fage")
        if lines and isinstance(lines[0],Mapping) and lines[0].get("text")!=blueprint.get("opening_claim"): failures.append("monologue must open with its claim")
    elif mode=="story":
        if "发哥" not in speakers or not any(s!="发哥" for s in speakers): failures.append("story requires stakeholder and Fage")
    actions=script.get("key_actions")
    if not isinstance(actions,list): failures.append("key_actions must be array");actions=[]
    action_ids=[]
    for action in actions:
        if not isinstance(action,Mapping): failures.append("action must be object");continue
        if set(action)!={"action_id","after_line_id","actor","action","consequence"}: failures.append("action keys differ from contract")
        for key in ("action_id","actor","action","consequence"): legacy._require_text(action,key,"action."+key,failures)
        action_ids.append(action.get("action_id"))
        if action.get("after_line_id") not in ids: failures.append("action references missing line")
        if action.get("actor")=="发哥": failures.append("persona boundary: use shots for Fage speaking; consequential actions belong to stakeholder")
    if len(set(action_ids))!=len(action_ids): failures.append("duplicate action IDs")
    shots=script.get("necessary_shots")
    if not isinstance(shots,list) or not shots or any(not isinstance(s,str) or not s.strip() for s in shots): failures.append("necessary_shots must be non-empty text array")
    ending=script.get("ending")
    if not isinstance(ending,Mapping) or set(ending)!={"kind","consequence"}: failures.append("ending keys differ from contract")
    elif ending.get("kind") not in {"advice","decision","action","open_question"} or not isinstance(ending.get("consequence"),str) or not ending["consequence"].strip(): failures.append("invalid ending")
    failures.extend(boundary_failures(script))
    if isinstance(persona,Mapping):
        fage_lines=[line for line in lines if isinstance(line,Mapping) and line.get("speaker")=="发哥"]
        legacy._validate_forbidden_biography({"lines":fage_lines},persona,failures)
        for text in legacy._all_text(script):
            if re.search(r"发哥(?:的)?(?:妻子|老婆|儿子|女儿|父亲|母亲|婚姻|籍贯|创业经历)",text):
                failures.append("forbidden biography: narrated Fage personal facts")

    for key,path in legacy._recursive_key_paths(data):
        if key in legacy.FORBIDDEN_HUMAN_KEYS: failures.append("human evaluation field forbidden: "+path)
        if key in {"tts","read_aloud_timing","median_seconds"}: failures.append("unmeasured timing field forbidden: "+path)
    return legacy.IntegrityResult(failures)
