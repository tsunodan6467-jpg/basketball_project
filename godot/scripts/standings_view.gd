extends Control

## 順位表用 JSON（Python 手動配置を優先し、無ければ同梱モック）
var _standings_json_paths: Array[String] = [
	"res://data/standings_from_python.json",
	"res://data/standings_mock.json",
]

const _LOAD_FAILED_MESSAGE := "順位表データ読込に失敗しました"

var _last_loaded_uri: String = ""

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _context_meta: Label = %ContextMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _summary_block: Label = %SummaryBlockLabel
@onready var _footer_note: Label = %FooterNoteLabel
@onready var _scroll_content: VBoxContainer = %ScrollContent


func _ready() -> void:
	_apply_snapshot(_load_standings_snapshot())


func _load_standings_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _standings_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f := FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[standings_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text := f.get_as_text()
		var parsed = JSON.parse_string(text)
		if parsed == null:
			push_warning("[standings_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[standings_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data := parsed as Dictionary
		_last_loaded_uri = path
		print("[standings_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("standings_from_python.json"):
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
		_context_meta.text = ""
		_readonly_strip.text = "読み取り専用"
		_summary_block.text = "—"
		_footer_note.text = ""
		return

	_status_label.visible = false
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_screen_title.text = _txt(d, "screen_title", "順位表（閲覧）")
	_team_name.text = _txt(d, "team_name", "自クラブ")

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	var cur_div: String = _str_cell(summary.get("current_division", null))
	var hs_text: String = _has_season_label(summary.get("has_season", null))
	var season_line: String = _txt(d, "season_label", "—")
	_context_meta.text = "シーズン: %s\n現在所属（summary）: %s ／ シーズン接続: %s" % [season_line, cur_div, hs_text]

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存は行いません）"

	var div_count_s: String = _int_display_cell(summary.get("division_count", null))
	_summary_block.text = "現在所属（summary）: %s\nディビジョン数: %s\nシーズン接続: %s" % [cur_div, div_count_s, hs_text]

	var notes := _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_footer_note.text = "読み取り専用。進行・編集・保存は行いません。"
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
	_add_scroll_heading("ディビジョン別順位")
	var divs_raw: Variant = d.get("divisions", null)
	var divs := _array_or_empty(divs_raw)
	if divs.is_empty():
		_add_scroll_paragraph("（divisions がありません）", 12, Color(0.62, 0.66, 0.74, 1))
		return

	var first_div: bool = true
	for item in divs:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var div: Dictionary = item as Dictionary
		if not first_div:
			_scroll_content.add_child(HSeparator.new())
		first_div = false
		_add_division_block(div)


func _add_division_block(div: Dictionary) -> void:
	var label_s: String = _str_cell(div.get("division_label", null))
	var lvl_v: Variant = div.get("level", null)
	var title: String = label_s
	if lvl_v != null and str(lvl_v).strip_edges() != "":
		title = "%s（level %s）" % [label_s, str(lvl_v).strip_edges()]
	_add_scroll_subheading(title)

	var rows_raw: Variant = div.get("rows", null)
	var rows := _array_or_empty(rows_raw)
	var empty_msg: String = str(div.get("empty_message", "")).strip_edges()

	if rows.is_empty():
		var msg: String = empty_msg
		if msg.is_empty():
			msg = "（このディビジョンに順位行がありません）"
		_add_scroll_paragraph(msg, 12, Color(0.7, 0.74, 0.82, 1))
		return

	_add_standings_header_row()
	for row_item in rows:
		if typeof(row_item) != TYPE_DICTIONARY:
			continue
		_add_standings_data_row(row_item as Dictionary)


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


func _standings_col_width(idx: int) -> float:
	var w: Array[float] = [40.0, 200.0, 40.0, 40.0, 56.0, 56.0, 64.0, 32.0]
	if idx >= 0 and idx < w.size():
		return w[idx]
	return 72.0


func _add_standings_header_row() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var headers: Array[String] = ["順位", "クラブ", "勝", "敗", "得点", "失点", "得失点", "自"]
	for i in range(headers.size()):
		var h: String = headers[i]
		var lab := Label.new()
		lab.text = h
		lab.add_theme_color_override("font_color", Color(0.82, 0.88, 0.96, 1))
		lab.add_theme_font_size_override("font_size", 12)
		lab.custom_minimum_size.x = _standings_col_width(i)
		lab.clip_text = true
		if i in [2, 3, 4, 5, 6]:
			lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		if i in [0, 7]:
			lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		row.add_child(lab)
	_scroll_content.add_child(row)
	_scroll_content.add_child(HSeparator.new())


func _add_standings_data_row(row: Dictionary) -> void:
	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 8)
	var is_user: bool = _is_user_row_from_dict(row)

	var rank_s: String = _int_display_cell(row.get("rank", null))
	var team_s: String = _str_cell(row.get("team_name", null))
	var wins_s: String = _int_display_cell(row.get("wins", null))
	var losses_s: String = _int_display_cell(row.get("losses", null))
	var pf_s: String = _int_display_cell(row.get("points_for", null))
	var pa_s: String = _int_display_cell(row.get("points_against", null))
	var diff_s: String = _diff_display_cell(row.get("point_diff", null))
	var badge_s: String = "自" if is_user else ""

	var cells: Array[String] = [rank_s, team_s, wins_s, losses_s, pf_s, pa_s, diff_s, badge_s]
	for i in range(cells.size()):
		var s: String = cells[i]
		var lab := Label.new()
		lab.text = s
		if is_user:
			lab.add_theme_color_override("font_color", Color(0.96, 0.98, 1.0, 1))
		else:
			lab.add_theme_color_override("font_color", Color(0.88, 0.91, 0.96, 1))
		lab.add_theme_font_size_override("font_size", 12)
		lab.custom_minimum_size.x = _standings_col_width(i)
		lab.clip_text = true
		if i in [2, 3, 4, 5, 6]:
			lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		if i in [0, 7]:
			lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		if i == 1:
			var team_raw: Variant = row.get("team_name", null)
			if team_s != "-" and team_raw != null:
				var tip: String = str(team_raw).strip_edges()
				if not tip.is_empty():
					lab.tooltip_text = tip
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


func _has_season_label(v: Variant) -> String:
	if v == null:
		return "不明"
	if typeof(v) == TYPE_BOOL:
		return "あり" if v else "なし"
	if typeof(v) == TYPE_STRING:
		var t: String = str(v).strip_edges().to_lower()
		if t in ["true", "1", "yes"]:
			return "あり"
		if t in ["false", "0", "no"]:
			return "なし"
	return "不明"


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


func _diff_display_cell(v: Variant) -> String:
	if v == null:
		return "-"
	var n: int = 0
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		n = int(v)
	elif typeof(v) == TYPE_STRING:
		var t: String = str(v).strip_edges()
		if t.is_empty():
			return "-"
		if t.is_valid_int():
			n = int(t)
		elif t.is_valid_float():
			n = int(float(t))
		else:
			return "-"
	else:
		return "-"
	if n > 0:
		return "+%d" % n
	return str(n)


func _is_user_row_from_dict(row: Dictionary) -> bool:
	var v: Variant = row.get("is_user_row", false)
	if typeof(v) == TYPE_BOOL:
		return v
	if typeof(v) == TYPE_INT:
		return int(v) != 0
	if typeof(v) == TYPE_FLOAT:
		return int(v) != 0
	if typeof(v) == TYPE_STRING:
		var s: String = str(v).strip_edges().to_lower()
		return s in ["true", "1", "yes"]
	return false
