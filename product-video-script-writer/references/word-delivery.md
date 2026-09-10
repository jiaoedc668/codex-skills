# Word 交付契约

只有当前完整文案对应的选择事件和其后的明确确认事件同时存在，才可生成 Word。任何修订都改变文案哈希，旧确认立即失效。

确认后准备 UTF-8 JSON：

```json
{
  "candidate_id": "m1",
  "format": "monologue",
  "theme": "主题",
  "estimated_seconds": 30,
  "full_copy": "已确认的当前完整文案",
  "props": ["产品", "少量道具"],
  "scenes": ["普通办公室"],
  "shot_plan": [
    {
      "time_range": "0-3 秒",
      "visual_action": "产品与动作",
      "line": "本段台词",
      "subtitle_hint": "字幕重点，没有则写无",
      "shooting_note": "手机竖屏、景别或表演提醒"
    }
  ]
}
```

`shot_plan` 的台词依次连读后必须与 `full_copy` 同义且不增加产品事实。台词列保持最宽，不用固定行高，表格允许自然跨页。

运行：

```powershell
python <skill-dir>/scripts/manage_workspace.py can-generate-word --workspace-root <state-root> --product-id <id> --copy-file <copy.txt>
python <skill-dir>/scripts/generate_word_cli.py --workspace-root <state-root> --product-id <id> --input <final-script.json> --output-root <output-root>
```

生成器按 `V1`、`V2` 递增，不覆盖既有文件。随后必须用 `documents` Skill 打包的 `render_docx.py` 渲染并逐页视觉检查。测试产物只能放临时目录，检查完成后删除。
