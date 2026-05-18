extends Control

## オーナーミッション閲覧用（第8画面プロトタイプ）。Python 手動配置 JSON を優先し、無ければ同梱 mock。

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _owner_mission_json_paths: Array[String] = [
	"res://data/owner_mission_from_python.json",
	"res://data/owner_mission_mock.json",
]

const _LOAD_FAILED_MESSAGE := "オーナーミッション情報を読み込めませんでした。"

var _last_loaded_uri: String = ""

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _league_meta: Label = %LeagueMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _card_trust_body: Label = %CardTrustBody
@onready var _missions_body: VBoxContainer = %MissionsBody
@onready var _card_eval_body: Label = %CardEvalBody
@onready var _card_caution_body: Label = %CardCautionBody
@onready var _notes_footer: Label = %NotesFooterLabel


func _ready() -> void:
	_apply_snapshot(_load_owner_mission_snapshot())


func _load_owner_mission_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _owner_mission_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f: FileAccess = FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[owner_mission_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text: String = f.get_as_text()
		var parsed: Variant = JSON.parse_string(text)
		if parsed == null:
			push_warning("[owner_mission_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[owner_mission_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data: Dictionary = parsed as Dictionary
		_last_loaded_uri = path
		print("[owner_mission_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("owner_mission_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_missions_body()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_league_meta.text = ""
		_readonly_strip.text = ""
		_card_trust_body.text = "—"
		_card_eval_body.text = "—"
		_card_caution_body.text = "—"
		_notes_footer.text = ""
		return

	_status_label.visible = false
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_screen_title.text = _txt(d, "screen_title", "オーナーミッション（閲覧）")
	var tname: String = _txt(d, "team_name", "—")
	_team_name.text = tname
	var lv_raw: Variant = d.get("league_level", null)
	var lv_s: String = "—"
	if lv_raw != null:
		lv_s = "D%s" % str(lv_raw)
	_league_meta.text = "%s / %s" % [tname, lv_s]

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存・ミッション操作は行いません）"

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	_card_trust_body.text = _build_trust_card_text(summary)

	_fill_mission_rows(d.get("mission_items", null))
	_card_eval_body.text = _build_evaluation_text(d.get("evaluation_items", null))
	_card_caution_body.text = _build_caution_text(d.get("sections", null), d.get("notes", null))

	var notes: Array = _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_notes_footer.text = "読み取り専用。ミッション生成・評価更新・報酬付与などの操作は含みません。"
	else:
		_notes_footer.text = _join_lines(notes)


func _clear_missions_body() -> void:
	for c in _missions_body.get_children():
		c.queue_free()


func _fill_mission_rows(raw: Variant) -> void:
	var arr: Array = _array_or_empty(raw)
	if arr.is_empty():
		var lab := Label.new()
		lab.autowrap_mode = 2
		lab.add_theme_font_size_override("font_size", 13)
		lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		lab.text = "今季ミッションはありません。"
		_missions_body.add_child(lab)
		return
	for item in arr:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var m: Dictionary = item as Dictionary
		var block := _mission_block_text(m)
		var lab := Label.new()
		lab.autowrap_mode = 2
		lab.add_theme_font_size_override("font_size", 13)
		lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		lab.text = block
		_missions_body.add_child(lab)


func _mission_block_text(m: Dictionary) -> String:
	var title: String = str(m.get("title", "—"))
	var st: String = str(m.get("status_label", m.get("status", "—")))
	var prog: String = str(m.get("progress_label", "-"))
	var rew: String = str(m.get("reward", "-"))
	var pen: String = str(m.get("penalty", "-"))
	var memo: String = str(m.get("memo", ""))
	var lines: PackedStringArray = PackedStringArray([
		"【%s】 %s" % [title, st],
		"進捗: %s ／ 報酬: %s ／ ペナルティ: %s" % [prog, rew, pen],
	])
	if memo.strip_edges() != "":
		lines.append("メモ: " + memo.strip_edges())
	return "\n".join(lines)


func _build_trust_card_text(summary: Dictionary) -> String:
	var lbl: String = str(summary.get("owner_trust_label", "-"))
	var rank: String = str(summary.get("owner_trust_rank", "-"))
	var ot: Variant = summary.get("owner_trust", null)
	var ot_line: String = "数値: —"
	if ot != null:
		ot_line = "数値: %s" % str(ot)
	var sc: Variant = summary.get("season_count", null)
	var am: Variant = summary.get("at_annual_menu", null)
	var ctx: String = ""
	if sc != null:
		ctx += "シーズン回数: %s" % str(sc)
	if am != null:
		if ctx != "":
			ctx += " ／ "
		ctx += "年度メニュー直後: %s" % ("はい" if bool(am) else "いいえ")
	if ctx == "":
		ctx = "—"
	return "%s\nowner_trust_rank: %s\n%s\n%s" % [lbl, rank, ot_line, ctx]


func _build_evaluation_text(raw: Variant) -> String:
	var arr: Array = _array_or_empty(raw)
	if arr.is_empty():
		return "—"
	var parts: PackedStringArray = PackedStringArray()
	for it in arr:
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var e: Dictionary = it as Dictionary
		var lab: String = str(e.get("label", "—"))
		var disp: String = str(e.get("display_value", "—"))
		parts.append("%s: %s" % [lab, disp])
	return "\n".join(parts)


func _build_caution_text(sections_raw: Variant, notes_raw: Variant) -> String:
	var secs: Array = _array_or_empty(sections_raw)
	for sec in secs:
		if typeof(sec) != TYPE_DICTIONARY:
			continue
		var s: Dictionary = sec as Dictionary
		if str(s.get("title", "")) != "注意":
			continue
		var lines: Array = _array_or_empty(s.get("lines", null))
		if not lines.is_empty():
			return _join_lines(lines)
	var notes: Array = _array_or_empty(notes_raw)
	if not notes.is_empty():
		return _join_lines(notes)
	return "読み取り専用です。"


func _dict_or_empty(v: Variant) -> Dictionary:
	if typeof(v) == TYPE_DICTIONARY:
		return v as Dictionary
	return {}


func _array_or_empty(v: Variant) -> Array:
	if v == null:
		return []
	if typeof(v) == TYPE_ARRAY:
		return v as Array
	return []


func _join_lines(v: Variant) -> String:
	var a: Array = _array_or_empty(v)
	var parts: PackedStringArray = PackedStringArray()
	for x in a:
		parts.append(str(x))
	return "\n".join(parts)


func _txt(d: Dictionary, key: String, default_s: String) -> String:
	if not d.has(key):
		return default_s
	var v: Variant = d[key]
	if v == null:
		return default_s
	var s: String = str(v).strip_edges()
	return s if s != "" else default_s


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning(
			"[owner_mission_view] change_scene_to_file failed: %s err=%s"
			% [_HOME_DASHBOARD_SCENE_PATH, err]
		)
