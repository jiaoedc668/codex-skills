# 历史机制退役说明

旧版隔离语义审稿、公开审稿包、角色结论和汇总字段已退出生产，不再用于新候选、精修或 Word 门控。本文件仅保留该退役事实，供读取旧工件时识别来源。

当前生产候选统一使用 schema v6，schema v5保留历史兼容。单稿由 `check_candidate_integrity.py` 检查事实边界、人物引用、剧情或口播合同与客观边界；三稿由 `check_batch_integrity.py` 检查批次一致性、选题对应和因果骨架复用；历史重复由 `check_content_similarity.py` 检查。

这些命令只输出 `INTEGRITY PASS/FAIL`，不产生人工质量结论，也不能代替谢总对完整候选的明确评价。
