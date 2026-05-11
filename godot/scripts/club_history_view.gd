extends Control

## クラブ史用 JSON（Python 手動配置を優先し、無ければ同梱モック）
var _club_history_json_paths: Array[String] = [
	"res://data/club_history_from_python.json",
	"res://data/club_history_mock.json",
]

const _LOAD_FAILED_MESSAGE := "クラブ史データ読込に失敗しました"

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
	_apply_snapshot(_load_club_history_snapshot())


func _load_club_history_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _club_history_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f := FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[club_history_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text := f.get_as_text()
		var parsed = JSON.parse_string(text)
		if parsed == null:
			push_warning("[club_history_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[club_history_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data := parsed as Dictionary
		_last_loaded_uri = path
		print("[club_history_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("club_history_from_python.json"):
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

	_screen_title.text = _txt(d, "screen_title", "クラブ史（閲覧）")
	_team_name.text = _txt(d, "team_name", "自クラブ")

	var lv = d.get("league_level", null)
	var lv_s := "不明"
	if lv != null:
		lv_s = "D%s" % str(lv)
	_league_meta.text = "リーグ段階: %s" % lv_s

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存は行いません）"

	var summary := _dict_or_empty(d.get("summary", {}))
	var founded := _str_cell(summary.get("founded_label", null))
	var seasons := _int_display(summary.get("seasons_recorded", null))
	var titles := _int_display(summary.get("titles_count", null))
	var promo := _int_display(summary.get("promotions_count", null))
	var releg := _int_display(summary.get("relegations_count", null))
	var evc := _int_display(summary.get("history_events_count", null))
	_summary_block.text = (
		"設立表記: %s\n記録済みシーズン数: %s\nタイトル数: %s\n昇格数: %s\n降格数: %s\n出来事件数: %s"
		% [founded, seasons, titles, promo, releg, evc]
	)

	var notes := _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_footer_note.text = "読み取り専用。進行・編集・保存は行いません。"
	else:
		var sb := ""
		var first := true
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
	_add_scroll_heading("セクション")
	var sections := _array_or_empty(d.get("sections", null))
	if sections.is_empty():
		_add_scroll_paragraph("（セクションがありません）", 12, Color(0.62, 0.66, 0.74, 1))
	else:
		for item in sections:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var sec := item as Dictionary
			var st := _txt(sec, "title", "（無題）")
			_add_scroll_subheading(st)
			var lines_raw = sec.get("lines", null)
			var lines := _array_or_empty(lines_raw)
			if lines.is_empty():
				_add_scroll_paragraph("（本文なし）", 12, Color(0.62, 0.66, 0.74, 1))
			else:
				for line in lines:
					_add_scroll_paragraph(_str_cell(line), 12, Color(0.88, 0.9, 0.95, 1))

	_scroll_content.add_child(HSeparator.new())

	_add_scroll_heading("シーズン履歴")
	var seasons_rows := _array_or_empty(d.get("season_rows", null))
	if seasons_rows.is_empty():
		_add_scroll_paragraph("（シーズン履歴がありません）", 12, Color(0.62, 0.66, 0.74, 1))
	else:
		_add_season_table_header()
		for item in seasons_rows:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var row := item as Dictionary
			_add_season_table_row(row)

	_scroll_content.add_child(HSeparator.new())

	_add_scroll_heading("主な出来事")
	var events := _array_or_empty(d.get("events", null))
	if events.is_empty():
		_add_scroll_paragraph("（出来事がありません）", 12, Color(0.62, 0.66, 0.74, 1))
	else:
		for item in events:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var ev := item as Dictionary
			var ord_s := _str_cell(ev.get("order", null))
			var lab := _str_cell(ev.get("label", null))
			var body := _str_cell(ev.get("text", null))
			var line := "%s. [%s] %s" % [ord_s, lab, body]
			_add_scroll_paragraph(line, 12, Color(0.86, 0.9, 0.96, 1))


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


func _add_season_table_header() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var headers: Array[String] = ["シーズン", "所属", "戦績", "結果", "メモ"]
	for h in headers:
		var lab := Label.new()
		lab.text = h
		lab.add_theme_color_override("font_color", Color(0.72, 0.78, 0.88, 1))
		lab.add_theme_font_size_override("font_size", 11)
		lab.custom_minimum_size.x = _season_col_width(h)
		lab.clip_text = false
		lab.autowrap_mode = 2
		row.add_child(lab)
	_scroll_content.add_child(row)
	_scroll_content.add_child(HSeparator.new())


func _season_col_width(header: String) -> float:
	match header:
		"シーズン":
			return 100.0
		"所属":
			return 52.0
		"戦績":
			return 88.0
		"結果":
			return 120.0
		"メモ":
			return 360.0
		_:
			return 80.0


func _add_season_table_row(row: Dictionary) -> void:
	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 8)
	var cells: Array[String] = [
		_str_cell(row.get("season", null)),
		_str_cell(row.get("division", null)),
		_str_cell(row.get("record", null)),
		_str_cell(row.get("result", null)),
		_str_cell(row.get("note", null)),
	]
	var headers: Array[String] = ["シーズン", "所属", "戦績", "結果", "メモ"]
	for i in range(cells.size()):
		var lab := Label.new()
		lab.text = cells[i]
		lab.add_theme_color_override("font_color", Color(0.9, 0.92, 0.96, 1))
		lab.add_theme_font_size_override("font_size", 12)
		lab.custom_minimum_size.x = _season_col_width(headers[i])
		lab.autowrap_mode = 2
		lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hbox.add_child(lab)
	_scroll_content.add_child(hbox)


func _dict_or_empty(v: Variant) -> Dictionary:
	if typeof(v) == TYPE_DICTIONARY:
		return v as Dictionary
	return {}


func _array_or_empty(v: Variant) -> Array:
	if typeof(v) == TYPE_ARRAY:
		return v as Array
	return []


func _txt(d: Dictionary, key: String, fallback: String) -> String:
	var val = d.get(key, null)
	if val == null:
		return fallback
	var s := str(val).strip_edges()
	return s if not s.is_empty() else fallback


func _str_cell(v: Variant) -> String:
	if v == null:
		return "-"
	var s := str(v).strip_edges()
	return s if not s.is_empty() else "-"


func _int_display(v: Variant) -> String:
	if v == null:
		return "不明"
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		return str(int(v))
	if typeof(v) == TYPE_STRING:
		var t := str(v).strip_edges()
		if t.is_empty():
			return "不明"
		if t.is_valid_int():
			return str(int(t))
		if t.is_valid_float():
			return str(int(float(t)))
	return "不明"


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning("[club_history_view] change_scene_to_file failed: %s err=%s" % [_HOME_DASHBOARD_SCENE_PATH, err])
