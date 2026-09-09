# Codex Skills

谢总个人开发的 Codex Skill 仓库。

## 当前 Skill

- `boss-ip-video-script-writer/`：发哥老板 IP 自然流量短视频创作、校验和 Word 交付工具。

## 约定

- 每个 Skill 使用独立目录，目录名使用英文 kebab-case。
- Skill 的规则、参考资料、脚本和测试随 Skill 一起维护。
- 运行产物、个人内容库和正式交付文件不进入本仓库。
- 修改后先运行该 Skill 的定向测试，再提交 Git。

## 迭代流程

每次修改 Skill 后按以下顺序执行：

```powershell
python -m unittest discover -s boss-ip-video-script-writer/tests -p "test_*.py" -q
python -m compileall -q boss-ip-video-script-writer/scripts
git diff --check
git add -- boss-ip-video-script-writer
git commit -m "说明本次修改"
git push
git status
```

测试或检查未通过时不提交、不推送。推送后确认本地分支与 `origin/main` 同步。

各 Skill 独立版本管理；Boss IP 当前版本取自其 [SKILL.md](boss-ip-video-script-writer/SKILL.md) 的 `metadata.version`，变更见 [CHANGELOG](boss-ip-video-script-writer/CHANGELOG.md)，标签采用 `boss-ip-v<版本>`。迭代时只暂存本次审查过的 Skill 目录及明确受影响的仓库文档，禁止混入其他 Skill、业务内容库或临时产物。版本、人物迁移及文件整理细则见 [版本维护](boss-ip-video-script-writer/references/release-management.md)。
