extends Control

## 試合ログ（閲覧）— Python / mock JSON の match_logs[] を読み取り専用表示。

var _match_logs_json_paths: Array[String] = [
	"res://data/match_logs_from_python.json",
	"res://data/match_logs_mock.json",
]

const _LOAD_FAILED_MESSAGE := "試合ログデータ読込に失敗しました"
const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"
const _DETAIL_HINT := "試合を選択すると、実況 excerpt と key plays を表示します。"

var _last_loaded_uri: String = ""
var _detail_panel: PanelContainer = null
var _detail_style_normal: StyleBoxFlat = null
var _detail_style_error: StyleBoxFlat = null

@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _context_meta: Label = %ContextMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _status_label: Label = %StatusLabel
@onready var _scroll_content: VBoxContainer = %ScrollContent
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _footer_note_label: Label = %FooterNoteLabel


func _ready() -> void:
	_setup_detail_card_style()
	_apply_snapshot(_load_match_logs_snapshot())


func _load_match_logs_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _match_logs_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f: FileAccess = FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[match_logs_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text: String = f.get_as_text()
		var parsed: Variant = JSON.parse_string(text)
		if parsed == null:
			push_warning("[match_logs_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[match_logs_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data: Dictionary = parsed as Dictionary
		_last_loaded_uri = path
		print("[match_logs_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("match_logs_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_scroll()
	if d.has("_error"):
		_show_status_message(str(d["_error"]), true)
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_context_meta.text = ""
		_readonly_strip.text = "読み取り専用"
		_footer_note_label.text = ""
		return

	_set_detail_card_visible(false)
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_screen_title.text = _txt(d, "screen_title", "試合ログ（閲覧）")
	_team_name.text = _txt(d, "team_name", "自クラブ")

	var summary: Dictionary = _dict_value(d.get("summary", null))
	var count_s: String = _int_display_cell(summary.get("count", null))
	var exported_s: String = _int_display_cell(summary.get("exported_count", null))
	var latest_s: String = _int_display_cell(summary.get("latest_round", null))
	var cr_s: String = _int_display_cell(summary.get("current_round", null))
	var tr_s: String = _int_display_cell(summary.get("total_rounds", null))
	var season_line: String = _txt(d, "season_label", "—")
	_context_meta.text = (
		"シーズン: %s\n保存 %s 件（表示 %s）・最新 R%s ・ 現在 R%s/%s"
		% [season_line, count_s, exported_s, latest_s, cr_s, tr_s]
	)

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存は行いません）"

	var notes: Array = _array_value(d.get("notes", null))
	if notes.is_empty():
		_footer_note_label.text = "読み取り専用。進行・編集・保存は行いません。"
	else:
		var sb: String = ""
		var first_note: bool = true
		for n in notes:
			var cell: String = _str_cell(n)
			if cell.is_empty() or cell == "-":
				continue
			if not first_note:
				sb += " ／ "
			first_note = false
			sb += cell
		_footer_note_label.text = sb if not sb.is_empty() else "読み取り専用。進行・編集・保存は行いません。"

	_status_label.text = _DETAIL_HINT
	_set_detail_card_visible(true, false)

	var logs_raw: Variant = d.get("match_logs", null)
	var logs: Array = _array_value(logs_raw)
	var empty_msg: String = str(d.get("empty_message", "")).strip_edges()
	var has_logs: bool = bool(summary.get("has_logs", logs.size() > 0))

	if logs.is_empty() or not has_logs:
		if not empty_msg.is_empty():
			_add_empty_message_block(empty_msg)
		return

	_add_section_heading("保存済み試合ログ")
	var n: int = logs.size()
	for i in range(n):
		var item: Variant = logs[i]
		if typeof(item) != TYPE_DICTIONARY:
			continue
		_add_match_log_row(item as Dictionary)
		if i < n - 1:
			_scroll_content.add_child(HSeparator.new())


func _clear_scroll() -> void:
	for c in _scroll_content.get_children():
		c.queue_free()


func _add_section_heading(text: String) -> void:
	var panel := PanelContainer.new()
	panel.theme_type_variation = &"Phase4SummaryCard"
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 4)
	var title := Label.new()
	title.text = text
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(title)
	panel.add_child(inner)
	_scroll_content.add_child(panel)


func _add_empty_message_block(empty_msg: String) -> void:
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _make_row_style())
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 6)
	var title := Label.new()
	title.text = "お知らせ"
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(title)
	var body_lab := Label.new()
	body_lab.text = empty_msg
	body_lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body_lab.add_theme_font_size_override("font_size", 15)
	body_lab.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	body_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(body_lab)
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 4)
	margin.add_theme_constant_override("margin_top", 2)
	margin.add_theme_constant_override("margin_right", 4)
	margin.add_theme_constant_override("margin_bottom", 2)
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	margin.add_child(inner)
	panel.add_child(margin)
	_scroll_content.add_child(panel)


func _add_match_log_row(entry: Dictionary) -> void:
	var round_s: String = _int_display_cell(entry.get("round", null))
	var comp_s: String = _str_cell(entry.get("competition_type", null))
	var stage_s: String = _str_cell(entry.get("stage", null))
	var summary_s: String = _str_cell(entry.get("summary_line", null))
	var total_lines: int = _commentary_total_lines(entry)
	var key_count: int = _array_value(entry.get("key_plays", null)).size()

	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _make_row_style())
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 6)

	var meta_row := HBoxContainer.new()
	meta_row.add_theme_constant_override("separation", 8)
	meta_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var meta_parts: Array[String] = [
		"R%s" % round_s if round_s != "-" else "R-",
		comp_s,
		stage_s,
	]
	for i in range(meta_parts.size()):
		if i > 0:
			var sep := Label.new()
			sep.text = " ／ "
			sep.add_theme_font_size_override("font_size", 12)
			sep.add_theme_color_override("font_color", Color(0.35, 0.4, 0.5, 1))
			meta_row.add_child(sep)
		var meta_lab := Label.new()
		meta_lab.text = meta_parts[i]
		meta_lab.add_theme_font_size_override("font_size", 12)
		meta_lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		if i == 1:
			meta_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			meta_lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			meta_lab.clip_text = true
		meta_row.add_child(meta_lab)

	var detail_btn := Button.new()
	detail_btn.text = "詳細"
	detail_btn.flat = true
	detail_btn.custom_minimum_size = Vector2(36, 0)
	detail_btn.add_theme_font_size_override("font_size", 11)
	detail_btn.pressed.connect(_show_match_log_detail.bind(entry.duplicate()))
	meta_row.add_child(detail_btn)
	inner.add_child(meta_row)

	var summary_lab := Label.new()
	summary_lab.text = summary_s
	summary_lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	summary_lab.add_theme_font_size_override("font_size", 16)
	summary_lab.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	summary_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(summary_lab)

	var sub_lab := Label.new()
	sub_lab.text = "実況 %d 行 / key plays %d 件" % [total_lines, key_count]
	sub_lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	sub_lab.add_theme_font_size_override("font_size", 11)
	sub_lab.add_theme_color_override("font_color", Color(0.32, 0.36, 0.48, 1))
	sub_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(sub_lab)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 4)
	margin.add_theme_constant_override("margin_top", 2)
	margin.add_theme_constant_override("margin_right", 4)
	margin.add_theme_constant_override("margin_bottom", 2)
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	margin.add_child(inner)
	panel.add_child(margin)
	_scroll_content.add_child(panel)


func _show_match_log_detail(entry: Dictionary) -> void:
	var summary_s: String = _str_cell(entry.get("summary_line", null))
	var round_s: String = _int_display_cell(entry.get("round", null))
	var comp_s: String = _str_cell(entry.get("competition_type", null))
	var stage_s: String = _str_cell(entry.get("stage", null))
	var home_s: String = _str_cell(entry.get("home_team", null))
	var away_s: String = _str_cell(entry.get("away_team", null))
	var hs: String = _int_display_cell(entry.get("home_score", null))
	var als: String = _int_display_cell(entry.get("away_score", null))
	var result_s: String = _str_cell(entry.get("user_result", null))

	var excerpt: Dictionary = _dict_value(entry.get("commentary_excerpt", null))
	var head: Array = _array_value(excerpt.get("head", null))
	var tail: Array = _array_value(excerpt.get("tail", null))
	var total_lines: int = _commentary_total_lines(entry)
	var key_plays: Array = _array_value(entry.get("key_plays", null))

	var lines: PackedStringArray = PackedStringArray()
	lines.append("試合ログ詳細")
	lines.append(summary_s)
	lines.append("")
	lines.append("ラウンド: R%s / %s / %s" % [round_s, comp_s, stage_s])
	lines.append("対戦: %s vs %s" % [home_s, away_s])
	lines.append("スコア: %s - %s / 結果: %s" % [hs, als, result_s])
	lines.append("")
	lines.append("--- 開始直後 ---")
	if head.is_empty():
		lines.append("（excerpt なし）")
	else:
		for line in head:
			lines.append(str(line))
	lines.append("")
	lines.append("--- 終盤 ---")
	if tail.is_empty():
		lines.append("（excerpt なし）")
	else:
		for line in tail:
			lines.append(str(line))
	lines.append("")
	lines.append("全 %d 行中、先頭/末尾 excerpt のみ" % total_lines)
	lines.append("")
	lines.append("--- Key plays ---")
	if key_plays.is_empty():
		lines.append("（key plays なし）")
	else:
		for play_v in key_plays:
			if typeof(play_v) != TYPE_DICTIONARY:
				continue
			lines.append(_key_play_text(play_v as Dictionary))
	lines.append("")
	lines.append("※ full PBP ではありません。読み取り専用 excerpt です。")

	_status_label.text = "\n".join(lines)
	_set_detail_card_visible(true, false)


func _show_status_message(message: String, is_error: bool) -> void:
	_status_label.text = message
	_set_detail_card_visible(true, is_error)


func _make_row_style() -> StyleBoxFlat:
	var row_bg := StyleBoxFlat.new()
	row_bg.bg_color = Color(0.965, 0.975, 0.99, 1)
	row_bg.content_margin_left = 4.0
	row_bg.content_margin_top = 4.0
	row_bg.content_margin_right = 4.0
	row_bg.content_margin_bottom = 4.0
	row_bg.corner_radius_top_left = 2
	row_bg.corner_radius_top_right = 2
	row_bg.corner_radius_bottom_right = 2
	row_bg.corner_radius_bottom_left = 2
	return row_bg


func _make_detail_panel_style(bg: Color, border: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(1)
	style.set_corner_radius_all(6)
	style.content_margin_left = 10.0
	style.content_margin_top = 10.0
	style.content_margin_right = 10.0
	style.content_margin_bottom = 10.0
	return style


func _setup_detail_card_style() -> void:
	if _detail_panel != null:
		return

	_detail_style_normal = _make_detail_panel_style(
		Color(0.92, 0.96, 1.0, 1),
		Color(0.48, 0.64, 0.86, 1),
	)
	_detail_style_error = _make_detail_panel_style(
		Color(1.0, 0.94, 0.94, 1),
		Color(0.86, 0.48, 0.48, 1),
	)

	var parent := _status_label.get_parent()
	var idx := _status_label.get_index()

	_detail_panel = PanelContainer.new()
	_detail_panel.add_theme_stylebox_override("panel", _detail_style_normal)
	_detail_panel.visible = false
	_detail_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var margin := MarginContainer.new()
	parent.remove_child(_status_label)
	margin.add_child(_status_label)
	_detail_panel.add_child(margin)
	parent.add_child(_detail_panel)
	parent.move_child(_detail_panel, idx)

	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_status_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	_status_label.add_theme_font_size_override("font_size", 14)
	_status_label.add_theme_constant_override("line_spacing", 4)
	_status_label.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	_status_label.visible = true


func _set_detail_card_visible(visible: bool, is_error: bool = false) -> void:
	if _detail_panel == null:
		_status_label.visible = visible
		if not visible:
			_status_label.text = ""
		return

	if not visible:
		_detail_panel.visible = false
		_status_label.text = ""
		return

	_detail_panel.add_theme_stylebox_override(
		"panel",
		_detail_style_error if is_error else _detail_style_normal,
	)
	_status_label.add_theme_color_override(
		"font_color",
		Color(1, 0.52, 0.48, 1) if is_error else Color(0.08, 0.11, 0.18, 1),
	)
	_detail_panel.visible = true
	_status_label.visible = true


func _commentary_total_lines(entry: Dictionary) -> int:
	var excerpt: Dictionary = _dict_value(entry.get("commentary_excerpt", null))
	var raw: Variant = excerpt.get("total_lines", 0)
	if typeof(raw) in [TYPE_INT, TYPE_FLOAT]:
		return int(raw)
	if typeof(raw) == TYPE_STRING and str(raw).strip_edges().is_valid_int():
		return str(raw).strip_edges().to_int()
	return 0


func _key_play_text(play: Dictionary) -> String:
	var quarter: String = _int_display_cell(play.get("quarter", null))
	var play_no: String = _int_display_cell(play.get("play_no", null))
	var result_type: String = _str_cell(play.get("result_type", null))
	var hs: String = _int_display_cell(play.get("home_score", null))
	var als: String = _int_display_cell(play.get("away_score", null))
	var text_s: String = _str_cell(play.get("commentary_text", null))
	if text_s == "-":
		text_s = _str_cell(play.get("text", null))
	return "Q%s #%s [%s] %s-%s %s" % [quarter, play_no, result_type, hs, als, text_s]


func _dict_value(v: Variant) -> Dictionary:
	if typeof(v) == TYPE_DICTIONARY:
		return v as Dictionary
	return {}


func _array_value(v: Variant) -> Array:
	if typeof(v) == TYPE_ARRAY:
		return v as Array
	return []


func _txt(d: Dictionary, key: String, fallback: String) -> String:
	var val: Variant = d.get(key, null)
	if val == null:
		return fallback
	var s: String = str(val).strip_edges()
	return s if not s.is_empty() else fallback


func _str_cell(v: Variant) -> String:
	if v == null:
		return "-"
	var s: String = str(v).strip_edges()
	return s if not s.is_empty() else "-"


func _int_display_cell(v: Variant) -> String:
	if v == null:
		return "-"
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		return str(int(v))
	if typeof(v) == TYPE_STRING:
		var t: String = str(v).strip_edges()
		if t.is_empty():
			return "-"
		if t.is_valid_int():
			return str(int(t))
		if t.is_valid_float():
			return str(int(float(t)))
	return "-"


func _on_home_nav_button_pressed() -> void:
	var err: Error = get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning(
			"[match_logs_view] change_scene_to_file failed: %s err=%s"
			% [_HOME_DASHBOARD_SCENE_PATH, err]
		)
