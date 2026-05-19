extends Control

## 日程閲覧用 JSON（Python 手動配置を優先し、無ければ同梱モック）
var _schedule_json_paths: Array[String] = [
	"res://data/schedule_from_python.json",
	"res://data/schedule_mock.json",
]

const _LOAD_FAILED_MESSAGE := "日程データ読込に失敗しました"

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _last_loaded_uri: String = ""

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _context_meta: Label = %ContextMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _summary_block: Label = %SummaryBlockLabel
@onready var _footer_note: Label = %FooterNoteLabel
@onready var _next_game_label: Label = %NextGameLabel
@onready var _next_game_competition: Label = %NextGameCompetitionLabel
@onready var _next_game_round: Label = %NextGameRoundLabel
@onready var _next_game_opponent: Label = %NextGameOpponentLabel
@onready var _next_game_ha: Label = %NextGameHomeAwayLabel
@onready var _next_game_status: Label = %NextGameStatusLabel
@onready var _scroll_content: VBoxContainer = %ScrollContent


func _ready() -> void:
	_apply_snapshot(_load_schedule_snapshot())


func _load_schedule_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _schedule_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f: FileAccess = FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[schedule_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text: String = f.get_as_text()
		var parsed: Variant = JSON.parse_string(text)
		if parsed == null:
			push_warning("[schedule_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[schedule_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data: Dictionary = parsed as Dictionary
		_last_loaded_uri = path
		print("[schedule_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("schedule_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_scroll()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_status_label.add_theme_color_override("font_color", Color(1, 0.52, 0.48, 1))
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_context_meta.text = ""
		_readonly_strip.text = "読み取り専用"
		_summary_block.text = "—"
		_footer_note.text = ""
		_reset_next_game_card("—")
		return

	_status_label.visible = false
	_status_label.remove_theme_color_override("font_color")
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_screen_title.text = _txt(d, "screen_title", "日程（閲覧）")
	_team_name.text = _txt(d, "team_name", "自クラブ")

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	var cr_s: String = _int_display_cell(summary.get("current_round", null))
	var tr_s: String = _int_display_cell(summary.get("total_rounds", null))
	var hs_text: String = _has_season_label(summary.get("has_season", null))
	var uc_s: String = _int_display_cell(summary.get("upcoming_count", null))
	var season_line: String = _txt(d, "season_label", "—")
	_context_meta.text = "シーズン: %s\nラウンド %s／%s ・ 接続: %s ・ upcoming（summary）: %s" % [season_line, cr_s, tr_s, hs_text, uc_s]

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存は行いません）"

	_summary_block.text = "has_season: %s\n現在ラウンド: %s\n総ラウンド: %s\nupcoming 件数（summary）: %s" % [hs_text, cr_s, tr_s, uc_s]

	var notes: Array = _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_footer_note.text = "読み取り専用。進行・編集・保存は行いません。"
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
		if sb.is_empty():
			_footer_note.text = "読み取り専用。進行・編集・保存は行いません。"
		else:
			_footer_note.text = sb

	var ng: Dictionary = _dict_or_empty(d.get("next_game", {}))
	_apply_next_game_card(ng)

	_fill_scroll_body(d)


func _reset_next_game_card(fallback: String) -> void:
	_next_game_label.text = fallback
	_next_game_competition.text = "大会: —"
	_next_game_round.text = "ラウンド表記: —"
	_next_game_opponent.text = "対戦: —"
	_next_game_ha.text = "H/A: —"
	_next_game_status.text = "status: —"


func _apply_next_game_card(ng: Dictionary) -> void:
	var label_v: Variant = ng.get("label", null)
	_next_game_label.text = _str_cell(label_v)
	_next_game_competition.text = "大会: %s" % _str_cell(ng.get("competition", null))
	_next_game_round.text = "ラウンド表記: %s" % _str_cell(ng.get("round_label", null))
	_next_game_opponent.text = "対戦: %s" % _str_cell(ng.get("opponent", null))
	_next_game_ha.text = "H/A: %s" % _str_cell(ng.get("home_away", null))
	_next_game_status.text = "status: %s" % _str_cell(ng.get("status", null))


func _clear_scroll() -> void:
	for c in _scroll_content.get_children():
		c.queue_free()


func _fill_scroll_body(d: Dictionary) -> void:
	var upcoming_raw: Variant = d.get("upcoming_games", null)
	var upcoming: Array = _array_or_empty(upcoming_raw)
	var empty_msg: String = str(d.get("empty_message", "")).strip_edges()

	if upcoming.is_empty() and not empty_msg.is_empty():
		_add_empty_message_block(empty_msg)

	if not upcoming.is_empty():
		_add_upcoming_section_heading()
		var n: int = upcoming.size()
		for i in range(n):
			var item: Variant = upcoming[i]
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var row: Dictionary = item as Dictionary
			_add_upcoming_block(row)

	var ah: Dictionary = _dict_or_empty(d.get("advance_hint", null))
	var block_v: Variant = ah.get("block", "")
	var one_v: Variant = ah.get("one_line", "")
	var block_s: String = str(block_v).strip_edges()
	var one_s: String = str(one_v).strip_edges()
	if not block_s.is_empty() or not one_s.is_empty():
		_add_advance_hint_block(block_s, one_s)


func _add_upcoming_section_heading() -> void:
	var panel: PanelContainer = PanelContainer.new()
	panel.theme_type_variation = &"Phase4SummaryCard"
	var inner: VBoxContainer = VBoxContainer.new()
	inner.add_theme_constant_override("separation", 4)
	var title: Label = Label.new()
	title.text = "今後の予定"
	title.autowrap_mode = 2
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(title)
	panel.add_child(inner)
	_scroll_content.add_child(panel)


func _add_upcoming_block(row: Dictionary) -> void:
	var round_label_v: Variant = row.get("round_label", null)
	var comp_label_v: Variant = row.get("competition_label", null)
	var ha_v: Variant = row.get("home_away", null)
	var round_s: String = _str_cell(round_label_v)
	var comp_s: String = _str_cell(comp_label_v)
	var ha_s: String = _str_cell(ha_v)

	var opp_v: Variant = row.get("opponent", null)
	var line2: String = "対戦: %s" % _str_cell(opp_v)

	var detail_v: Variant = row.get("detail", null)
	var label_v: Variant = row.get("label", null)
	var detail_s: String = str(detail_v).strip_edges()
	var label_s: String = str(label_v).strip_edges()
	var line3: String = ""
	if not detail_s.is_empty():
		line3 = detail_s
	elif label_s.is_empty() or label_s == "-":
		line3 = "—"
	else:
		line3 = "ラベル: %s" % label_s

	var panel: PanelContainer = PanelContainer.new()
	panel.theme_type_variation = &"Phase4SummaryCard"
	var inner: VBoxContainer = VBoxContainer.new()
	inner.add_theme_constant_override("separation", 6)

	var meta_row := HBoxContainer.new()
	meta_row.add_theme_constant_override("separation", 8)
	meta_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var meta_parts: Array[String] = [round_s, comp_s, ha_s]
	for i in range(meta_parts.size()):
		if i > 0:
			var sep := Label.new()
			sep.text = " ／ "
			sep.add_theme_font_size_override("font_size", 12)
			sep.add_theme_color_override("font_color", Color(0.35, 0.4, 0.5, 1))
			meta_row.add_child(sep)
		var meta_lab := Label.new()
		meta_lab.text = meta_parts[i]
		meta_lab.autowrap_mode = 0
		meta_lab.add_theme_font_size_override("font_size", 12)
		meta_lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		if i == 1:
			meta_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			meta_lab.autowrap_mode = 2
			meta_lab.clip_text = true
		meta_row.add_child(meta_lab)
	inner.add_child(meta_row)

	var l2: Label = Label.new()
	l2.text = line2
	l2.autowrap_mode = 2
	l2.add_theme_font_size_override("font_size", 16)
	l2.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	l2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(l2)

	var l3: Label = Label.new()
	l3.text = line3
	l3.autowrap_mode = 2
	l3.add_theme_font_size_override("font_size", 11)
	l3.add_theme_color_override("font_color", Color(0.32, 0.36, 0.48, 1))
	l3.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(l3)
	panel.add_child(inner)
	_scroll_content.add_child(panel)


func _add_advance_hint_block(block_s: String, one_s: String) -> void:
	var panel: PanelContainer = PanelContainer.new()
	panel.theme_type_variation = &"Phase4SummaryCard"
	var inner: VBoxContainer = VBoxContainer.new()
	inner.add_theme_constant_override("separation", 4)
	var title: Label = Label.new()
	title.text = "進行ヒント（advance_hint）"
	title.autowrap_mode = 2
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(title)
	if not block_s.is_empty():
		var block_lab: Label = Label.new()
		block_lab.text = block_s
		block_lab.autowrap_mode = 2
		block_lab.add_theme_font_size_override("font_size", 12)
		block_lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		block_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		inner.add_child(block_lab)
	if not one_s.is_empty():
		var one_lab: Label = Label.new()
		one_lab.text = one_s
		one_lab.autowrap_mode = 2
		one_lab.add_theme_font_size_override("font_size", 12)
		one_lab.add_theme_color_override("font_color", Color(0.2, 0.25, 0.36, 1))
		one_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		inner.add_child(one_lab)
	panel.add_child(inner)
	_scroll_content.add_child(panel)


func _add_empty_message_block(empty_msg: String) -> void:
	var panel: PanelContainer = PanelContainer.new()
	panel.theme_type_variation = &"Phase4SummaryCard"
	var inner: VBoxContainer = VBoxContainer.new()
	inner.add_theme_constant_override("separation", 4)
	var title: Label = Label.new()
	title.text = "お知らせ"
	title.autowrap_mode = 2
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(title)
	var body_lab: Label = Label.new()
	body_lab.text = empty_msg
	body_lab.autowrap_mode = 2
	body_lab.add_theme_font_size_override("font_size", 13)
	body_lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
	body_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_child(body_lab)
	panel.add_child(inner)
	_scroll_content.add_child(panel)


func _add_scroll_heading(text: String) -> void:
	var lab: Label = Label.new()
	lab.text = text
	lab.add_theme_color_override("font_color", Color(0.94, 0.96, 0.99, 1))
	lab.add_theme_font_size_override("font_size", 17)
	lab.autowrap_mode = 2
	_scroll_content.add_child(lab)


func _add_scroll_paragraph(text: String, font_size: int, col: Color) -> void:
	var lab: Label = Label.new()
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


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err: Error = get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning("[schedule_view] change_scene_to_file failed: %s err=%s" % [_HOME_DASHBOARD_SCENE_PATH, err])
