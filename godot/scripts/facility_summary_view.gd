extends Control

## 施設サマリー閲覧用 JSON（Python 手動配置を優先し、無ければ同梱モック）
var _facility_summary_json_paths: Array[String] = [
	"res://data/facility_summary_from_python.json",
	"res://data/facility_summary_mock.json",
]

const _LOAD_FAILED_MESSAGE := "施設サマリーデータ読込に失敗しました"

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _last_loaded_uri: String = ""

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _league_meta: Label = %LeagueMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _summary_block: Label = %SummaryBlockLabel
@onready var _footer_note: Label = %FooterNoteLabel
@onready var _scroll_content: VBoxContainer = %ScrollContent


func _ready() -> void:
	_apply_snapshot(_load_facility_summary_snapshot())


func _load_facility_summary_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _facility_summary_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f: FileAccess = FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[facility_summary_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text: String = f.get_as_text()
		var parsed: Variant = JSON.parse_string(text)
		if parsed == null:
			push_warning("[facility_summary_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[facility_summary_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data: Dictionary = parsed as Dictionary
		_last_loaded_uri = path
		print("[facility_summary_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("facility_summary_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_scroll()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_league_meta.text = ""
		_readonly_strip.text = "読み取り専用"
		_summary_block.text = "—"
		_footer_note.text = ""
		return

	_status_label.visible = false
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_screen_title.text = _txt(d, "screen_title", "施設サマリー（閲覧）")
	_team_name.text = _txt(d, "team_name", "自クラブ")

	var lv_raw: Variant = d.get("league_level", null)
	var lv_s: String = "不明"
	if lv_raw != null:
		lv_s = "D%s" % str(lv_raw)
	_league_meta.text = "リーグ段階: %s" % lv_s

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存・施設投資は行いません）"

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	var pts_raw: Variant = summary.get("facility_upgrade_points", null)
	var pts_s: String = _int_display_cell(pts_raw)
	var avg_raw: Variant = summary.get("average_level", null)
	var avg_s: String = str(avg_raw).strip_edges()
	if avg_s.is_empty():
		avg_s = "-"
	var mx_raw: Variant = summary.get("max_level", null)
	var mx_s: String = _int_display_cell(mx_raw)
	var fc_raw: Variant = summary.get("facility_count", null)
	var fc_s: String = _int_display_cell(fc_raw)
	_summary_block.text = (
		"施設強化ポイント: %s\n平均施設レベル: %s（上限 %s）\n施設数: %s"
		% [pts_s, avg_s, mx_s, fc_s]
	)

	var notes: Array = _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_footer_note.text = "読み取り専用。施設投資・レベルアップ操作は含みません。"
	else:
		var sb: String = ""
		var first: bool = true
		for n in notes:
			if not first:
				sb += "\n"
			first = false
			sb += _str_cell(n)
		_footer_note.text = sb

	_fill_scroll_body(d)


func _clear_scroll() -> void:
	for c in _scroll_content.get_children():
		c.queue_free()


func _fill_scroll_body(d: Dictionary) -> void:
	_add_scroll_heading("施設一覧")
	var facilities_raw: Variant = d.get("facilities", null)
	var facilities: Array = _array_or_empty(facilities_raw)
	if facilities.is_empty():
		_add_scroll_paragraph("（施設データがありません）", 12, Color(0.62, 0.66, 0.74, 1))
	else:
		for item in facilities:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var row: Dictionary = item as Dictionary
			var label_s: String = str(row.get("label", "-")).strip_edges()
			if label_s.is_empty():
				label_s = "-"
			var level_label_s: String = str(row.get("level_label", "-")).strip_edges()
			if level_label_s.is_empty():
				level_label_s = "-"
			var line1: String = "%s  %s" % [label_s, level_label_s]
			_add_scroll_paragraph(line1, 13, Color(0.9, 0.94, 0.99, 1))
			var hint_raw: Variant = row.get("effect_hint", null)
			var hint_s: String = str(hint_raw).strip_edges()
			if hint_s.is_empty():
				hint_s = "-"
			var line2: String = "   %s" % hint_s
			_add_scroll_paragraph(line2, 12, Color(0.72, 0.76, 0.84, 1))

	_scroll_content.add_child(HSeparator.new())

	_add_scroll_heading("セクション")
	var sections_raw: Variant = d.get("sections", null)
	var sections: Array = _array_or_empty(sections_raw)
	if sections.is_empty():
		_add_scroll_paragraph("（セクションがありません）", 12, Color(0.62, 0.66, 0.74, 1))
	else:
		for sec_item in sections:
			if typeof(sec_item) != TYPE_DICTIONARY:
				continue
			var sec: Dictionary = sec_item as Dictionary
			var st: String = _txt(sec, "title", "（無題）")
			_add_scroll_subheading(st)
			var lines_raw: Variant = sec.get("lines", null)
			var lines: Array = _array_or_empty(lines_raw)
			if lines.is_empty():
				_add_scroll_paragraph("（本文なし）", 12, Color(0.62, 0.66, 0.74, 1))
			else:
				for line in lines:
					var line_s: String = _str_cell(line)
					_add_scroll_paragraph(line_s, 12, Color(0.88, 0.9, 0.95, 1))


func _add_scroll_heading(text: String) -> void:
	var lab := Label.new()
	lab.text = text
	lab.add_theme_color_override("font_color", Color(0.94, 0.96, 0.99, 1))
	lab.add_theme_font_size_override("font_size", 17)
	lab.autowrap_mode = 2
	_scroll_content.add_child(lab)


func _add_scroll_subheading(text: String) -> void:
	var lab := Label.new()
	lab.text = text
	lab.add_theme_color_override("font_color", Color(0.82, 0.88, 0.96, 1))
	lab.add_theme_font_size_override("font_size", 14)
	lab.autowrap_mode = 2
	_scroll_content.add_child(lab)


func _add_scroll_paragraph(text: String, font_size: int, col: Color) -> void:
	var lab := Label.new()
	lab.text = text
	lab.add_theme_color_override("font_color", col)
	lab.add_theme_font_size_override("font_size", font_size)
	lab.autowrap_mode = 2
	lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll_content.add_child(lab)


func _dict_or_empty(v: Variant) -> Dictionary:
	if typeof(v) == TYPE_DICTIONARY:
		return v as Dictionary
	return {}


func _array_or_empty(v: Variant) -> Array:
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
	var st: String = str(v).strip_edges()
	if st.is_empty():
		return "-"
	if st.is_valid_int():
		return str(int(st))
	if st.is_valid_float():
		return str(int(float(st)))
	return "-"


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning("[facility_summary_view] change_scene_to_file failed: %s err=%s" % [_HOME_DASHBOARD_SCENE_PATH, err])
