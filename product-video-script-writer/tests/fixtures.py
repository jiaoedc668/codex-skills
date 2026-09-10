from __future__ import annotations

import copy
import hashlib
import json


def brief(fmt: str = "monologue", product_id: str = "test-cleaner-x1") -> dict:
    return {
        "product_id": product_id,
        "product_name": "测试专用虚构产品净桌便携清洁器 X1",
        "category": "桌面清洁小家电",
        "use": "清理键盘和桌面碎屑",
        "selling_points": ["一键启动", "可拆集尘盒", "USB-C 充电"],
        "target_customer": "经常在工位吃零食的上班族",
        "format": fmt,
        "model": "X1",
        "scene": "普通办公室",
        "cast_location": "一名演员，普通办公室",
        "must_include": [],
        "banned_expressions": ["最强", "全网第一"],
        "reference_videos": [],
    }


def facts_hash(value: dict) -> str:
    facts = {
        "product_name": value["product_name"],
        "category": value["category"],
        "use": value["use"],
        "selling_points": value["selling_points"],
        "model": value.get("model"),
        "must_include": value.get("must_include", []),
        "banned_expressions": value.get("banned_expressions", []),
    }
    raw = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def research() -> list[dict]:
    return [
        {"platform": "douyin", "url": "https://example.test/1", "published_at": "2026-08-11", "comparability_note": "同为桌面碎屑清洁小家电", "performance_evidence": "测试夹具：模拟公开高互动数据", "learned": "先展示桌面碎屑反差，再给解决动作"},
        {"platform": "douyin", "url": "https://example.test/2", "published_at": "2026-07-20", "comparability_note": "同为键盘清洁使用场景", "performance_evidence": "测试夹具：模拟公开高互动数据", "learned": "评论关心键盘缝是否好清理"},
        {"platform": "douyin", "url": "https://example.test/3", "published_at": "2026-06-05", "comparability_note": "同为办公室清洁产品", "performance_evidence": "测试夹具：模拟公开高互动数据", "learned": "短句推进，一次只讲一个核心利益"},
    ]


def candidate(candidate_id: str, fmt: str, theme: str, copy_text: str, seconds: int, point: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "format": fmt,
        "theme": theme,
        "creative_note": f"围绕{theme}展开，用真实工位动作承接卖点",
        "full_copy": copy_text,
        "estimated_seconds": seconds,
        "main_selling_point": point,
        "used_selling_points": [point],
        "fact_claims": [{"claim": point, "source_text": point}],
        "internal_notes": {"machine_only": True},
    }


def monologues() -> list[dict]:
    return [
        candidate("m1", "monologue", "键盘缝里的下午茶", "每次在工位吃完饼干，桌面好擦，键盘缝最难办。我现在顺手拿它一按就启动，沿着缝走一遍，碎屑很快集中起来。别等下班再拍键盘，吃完当场收拾，桌面看着也舒服。", 30, "一键启动"),
        candidate("m2", "monologue", "倒集尘盒的解压时刻", "你以为桌面挺干净，把这些细碎东西聚起来才知道有多少。这款的集尘盒可以直接拆下来，倒掉以后再装回去。整个动作就在工位完成，下午吃坚果留下的碎渣，不必一直留到晚上。", 32, "可拆集尘盒"),
        candidate("m3", "monologue", "工位少带一根线", "办公室小电器最怕找不到专用线。这台用 USB-C 充电，我桌上现成的线就能接。平时把键盘旁边的碎屑清一下，用完收进抽屉，不为一个小工具再占一个插头，工位能省心一点。", 29, "USB-C 充电"),
    ]


def stories() -> list[dict]:
    return [
        candidate("s1", "story", "同事借键盘前", "同事刚伸手要借键盘，我下意识按住了。不是舍不得，是午后的饼干碎还卡在缝里。我拿起清洁器一键启动，沿键盘走了一圈。几秒后我把键盘推过去，他笑着说，你这是早有准备。", 52, "一键启动"),
        candidate("s2", "story", "会议前的桌面救场", "会议提前十分钟改到我工位，桌上的坚果碎来不及慢慢擦。我把集尘盒装好，快速清完桌面。人到齐后，我拆下集尘盒把碎屑倒掉，桌面恢复清爽，会议也不用围着一堆零食残渣开。", 64, "可拆集尘盒"),
        candidate("s3", "story", "谁拿走了充电线", "我正要清桌面，同事把充电线拿走了。我问他拿的是不是 USB-C，他点头。我把自己的手机线接到清洁器上，继续收拾。一个小工具不用守着专用线，办公室里临时借一根也能对上。", 58, "USB-C 充电"),
    ]


def packet(fmt: str = "monologue") -> dict:
    value = brief(fmt)
    candidates = monologues() if fmt == "monologue" else stories()
    if fmt == "both":
        candidates = monologues() + stories()
    return {
        "schema_version": 1,
        "brief": copy.deepcopy(value),
        "product_facts_sha256": facts_hash(value),
        "research": research(),
        "research_fallback_reason": None,
        "candidates": candidates,
    }
