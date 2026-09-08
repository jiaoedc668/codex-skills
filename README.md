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
git add .
git commit -m "说明本次修改"
git push
git status
```

测试或检查未通过时不提交、不推送。推送后确认本地分支与 `origin/main` 同步。
