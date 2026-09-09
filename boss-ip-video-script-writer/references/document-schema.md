# v6 Word交付合同与V3样式

## 候选与制作分开
候选保持完整schema v6，普通确认哈希为delivery_contract.content_hash(candidate_doc)，覆盖候选全部字段。制作包不写回候选。

交付源envelope精确包含document_kind=boss_ip_delivery、schema_version=1、candidate_doc、production_package、delivery、lineage。
- production_package精确为scene、cast（role/visibility）、props（文字数组，可空）、storyboard（line_ids/action/shot）、subtitles。分镜按顺序覆盖全部台词一次，角色集合与说话人相等，口播仅发哥。字幕写“完整对白逐句同步，按自然停顿分行。”
- delivery为script_id和正数版本。剧情B、口播A，分别从01跨批次递增。
- 首次lineage=null；修订为source_path与source_sha256，指向真实旧源，candidate_id一致、revision_id和输出版本逐次加一。

## 两条授权路径
普通新稿由独立反馈台账提供选中事件，其后同批同身份同修订的copy_confirmation匹配完整候选哈希。用户要求生成后才能执行。可拍评价不能替代确认。

专项重写授权独立文件kind=rewrite_delivery_authorization，记录task_path/task_sha256、真实user_quote、scope和bindings。scope每项为candidate_id/script_id/old_source_path/old_source_sha256；bindings每项为script_id/source_sha256（完整envelope的规范JSON哈希）。原任务、旧源、新源及修订关系都须校验，不能写假copy_confirmation或direct_shoot，也不能超出用户明确授权范围。

授权记录是可审计证据，并非外部密码签名。任务原文和实际会话授权是信任来源；检查者须逐条核对scope与当次用户授权完全一致，不能只相信文件自称获准。

## 编号与生成
生成脚本/发哥老板IP/内部资料/编号登记.json为事件数组，每项有稳定candidate_id、script_id、format、batch_id、version、source_sha256、word_sha256，交付事件另有路径和授权引用。同稿修订保留稳定编号并递增版本，排版规范版本不等于文案版本。

使用generate_script_docx.py，v6额外要求--registry、--persona、--feedback-ledger；专项加--authorization，路径根用--workspace-root，输出位置用--output-root。输出目录先登记用途。生成器核对编号、授权和内容后新建Word及源JSON，再追加登记；不覆盖已有路径。不向选题或反馈台账补造事件。

旧v5仍由同一入口旧分支读取，原确认哈希和旧格式行为保持兼容。新版V3排版用于v6制作包；不要用旧build_batch.py覆盖已确认旧Word。

## 样式与交付门
沿用已确认V3字体及加粗：微软雅黑统一ascii/hAnsi/eastAsia/cs，角色名加粗，最后一句突出，标题与执行单层级一致。保留原页面边距、正文表格与低饱和底色，内容自然分页，不强塞两页。

每份必须核对完整对白、标题、编号、版本、分镜和字幕；实际用本机Word只读打开并导出，渲染所有页面逐页看截断、空页、溢出、孤行和文字大小。内容哈希、文件存在或结构测试不能代替视觉检查。源与Word文件SHA256写入核验记录并对应登记；当次源、映射、逐篇改进依据及核验记录一并交付，旧版保留。
