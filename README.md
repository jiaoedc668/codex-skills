# Codex Skills

谢总个人开发的 Codex Skill 仓库。

## 当前 Skill

- `boss-ip-video-script-writer/`：发哥老板 IP 自然流量短视频创作、校验和 Word 交付工具。
- `product-video-script-writer/`：产品资料到自然流量口播或剧情候选、确认后拍摄 Word 及学习台账工具。

## 约定

- 每个 Skill 使用独立目录，目录名使用英文 kebab-case。
- Skill 的规则、参考资料、脚本和测试随 Skill 一起维护。
- 原始运行产物、个人内容库、完整台账和正式交付文件不进入本仓库；允许为普通 ChatGPT Chat 提交经过脱敏、压缩和公开安全检查的 `chat-context/` 只读快照。
- `chat-context/` 不是业务真相源，不得替代本地人物实例、反馈台账、选题台账或正式交付状态。
- 修改后先运行该 Skill 的定向测试，再提交 Git。

## ChatGPT 普通 Chat

`boss-ip-video-script-writer/CHATGPT.md` 仅用于普通 ChatGPT Chat 的环境适配；本地 Codex 正常执行 Skill 时忽略该文件。网页 Chat 通过 `chat-context/` 读取公开安全快照，缺失或未同步时按 `CHATGPT.md` 的 fallback 规则处理。

公开快照只由本地 Codex 在明确指定业务路径后同步：

```powershell
python <skill-dir>/scripts/sync_public_context.py --persona <business-root>/人物设定.json --feedback-ledger <business-root>/反馈台账.jsonl --topic-ledger <business-root>/选题台账.jsonl --shared-ledger <shared-root>/shared-creative-preferences.jsonl --output-dir <skill-dir>/chat-context
```

同步器只写固定白名单投影，业务状态仍以本地文件为准；失败时不会覆盖已有快照。

## 迭代流程

每次修改 Skill 后按以下顺序执行：

```powershell
python -m unittest discover -s boss-ip-video-script-writer/tests -p "test_*.py" -q
python -m compileall -q boss-ip-video-script-writer/scripts
git diff --check
git add -- boss-ip-video-script-writer README.md
git commit -m "说明本次修改"
git push
git status
```

测试或检查未通过时不提交、不推送。推送后确认本地分支与 `origin/main` 同步。

各 Skill 独立版本管理；Boss IP 当前版本取自其 [SKILL.md](boss-ip-video-script-writer/SKILL.md) 的 `metadata.version`，变更见 [CHANGELOG](boss-ip-video-script-writer/CHANGELOG.md)，标签采用 `boss-ip-v<版本>`。迭代时只暂存本次审查过的 Skill 目录及明确受影响的仓库文档，禁止混入其他 Skill、原始业务内容库或临时产物。版本、人物迁移及文件整理细则见 [版本维护](boss-ip-video-script-writer/references/release-management.md)。
