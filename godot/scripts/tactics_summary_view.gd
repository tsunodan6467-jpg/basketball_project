extends Control

## 戦術・ローテーションサマリー閲覧（第9画面プロトタイプ・単独確認用）。
## 今回は同梱 mock JSON のみ読み込む（from_python 優先は未実装）。

const _MOCK_JSON_PATH := "res://data/tactics_summary_mock.json"

const _LOAD_FAILED_MESSAGE := "戦術・ローテーション情報を読み込めませんでした。"

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _league_meta: Label = %LeagueMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _card_overview_body: Label = %CardOverviewBody
@onready var _card_attack_body: Label = %CardAttackBody
@onready var _card_defense_body: Label = %CardDefenseBody
@onready var _card_rotation_body: Label = %CardRotationBody
@onready var _player_roles_body: VBoxContainer = %PlayerRolesBody
@onready var _card_notes_body: Label = %CardNotesBody


func _ready() -> void:
	_apply_snapshot(_load_mock_snapshot())


func _load_mock_snapshot() -> Dictionary:
	if not FileAccess.file_exists(_MOCK_JSON_PATH):
		return {"_error": _LOAD_FAILED_MESSAGE}
	var f: FileAccess = FileAccess.open(_MOCK_JSON_PATH, FileAccess.READ)
	if f == null:
		return {"_error": _LOAD_FAILED_MESSAGE}
	var text: String = f.get_as_text()
	var parsed: Variant = JSON.parse_string(text)
	if parsed == null:
		return {"_error": _LOAD_FAILED_MESSAGE}
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"_error": _LOAD_FAILED_MESSAGE}
	print("[tactics_summary_view] Loaded JSON from: ", _MOCK_JSON_PATH)
	return parsed as Dictionary


func _apply_snapshot(d: Dictionary) -> void:
	_clear_player_roles()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_league_meta.text = ""
		_readonly_strip.text = ""
		_card_overview_body.text = "—"
		_card_attack_body.text = "—"
		_card_defense_body.text = "—"
		_card_rotation_body.text = "—"
		_card_notes_body.text = ""
		return

	_status_label.visible = false
	_data_source_label.text = "読込元: 同梱モックJSON / " + _MOCK_JSON_PATH

	_screen_title.text = _txt(d, "screen_title", "戦術・ローテーションサマリー（閲覧）")
	var tname: String = _txt(d, "team_name", "—")
	_team_name.text = tname
	var lv_raw: Variant = d.get("league_level", null)
	var lv_s: String = "—"
	if lv_raw != null:
		lv_s = "D%s" % str(lv_raw)
	_league_meta.text = "%s / %s" % [tname, lv_s]

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存・戦術変更は行いません）"

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	_card_overview_body.text = _build_overview_text(summary) + "\n\n" + _format_kv_items(_array_or_empty(d.get("tactic_items", null)))
	_card_attack_body.text = _build_attack_text(summary)
	_card_defense_body.text = _build_defense_text(summary)
	_card_rotation_body.text = _format_kv_items(_array_or_empty(d.get("rotation_items", null)))
	_fill_player_roles(_array_or_empty(d.get("player_role_items", null)))

	var notes: Array = _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_card_notes_body.text = "読み取り専用。戦術変更・ローテーション保存・先発自動決定などの操作は含みません。"
	else:
		_card_notes_body.text = _join_lines(notes)


func _clear_player_roles() -> void:
	for c in _player_roles_body.get_children():
		c.queue_free()


func _fill_player_roles(raw: Array) -> void:
	if raw.is_empty():
		var lab := Label.new()
		lab.autowrap_mode = 2
		lab.add_theme_font_size_override("font_size", 13)
		lab.add_theme_color_override("font_color", Color(0.86, 0.9, 0.95))
		lab.text = "選手ロール情報はありません。"
		_player_roles_body.add_child(lab)
		return
	var shown := 0
	for it in raw:
		if shown >= 8:
			break
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = it as Dictionary
		var line := _player_role_line(row)
		var lab := Label.new()
		lab.autowrap_mode = 2
		lab.add_theme_font_size_override("font_size", 13)
		lab.add_theme_color_override("font_color", Color(0.86, 0.9, 0.95))
		lab.text = line
		_player_roles_body.add_child(lab)
		shown += 1


func _player_role_line(row: Dictionary) -> String:
	var nm: String = str(row.get("player_name", "—"))
	var pos: String = str(row.get("position", "—"))
	var st: String = str(row.get("starter_label", "—"))
	var rl: String = str(row.get("role_label", "—"))
	var tm: String = str(row.get("target_minutes_label", "—"))
	var memo: String = str(row.get("memo", ""))
	var parts: PackedStringArray = PackedStringArray([
		"%s (%s) ／ %s ／ 役割: %s ／ 目標分数: %s" % [nm, pos, st, rl, tm],
	])
	if memo.strip_edges() != "":
		parts.append("  └ " + memo.strip_edges())
	return "\n".join(parts)


func _build_overview_text(summary: Dictionary) -> String:
	var preset: String = str(summary.get("tactic_preset_label", summary.get("tactic_preset", "—")))
	if preset.strip_edges() == "" or preset == "None":
		preset = "未設定"
	var psl: String = str(summary.get("play_style_label", summary.get("play_style", "—")))
	var ht: String = _bool_ja(summary.get("has_team_tactics", null))
	var hr: String = _bool_ja(summary.get("has_rotation_settings", null))
	var rpol: String = str(summary.get("rotation_policy_label", summary.get("rotation_policy", "—")))
	if rpol.strip_edges() == "" or rpol == "None":
		rpol = "—"
	return "戦術プリセット: %s\nプレイスタイル: %s\nhas_team_tactics: %s\nhas_rotation_settings: %s\nローテプリセット: %s" % [preset, psl, ht, hr, rpol]


func _build_attack_text(summary: Dictionary) -> String:
	return "オフェンステンポ: %s\nオフェンス傾向: %s\nオフェンス組み立て: %s\n3P方針: %s\nペイント方針: %s" % [
		str(summary.get("offense_tempo_label", "—")),
		str(summary.get("offense_focus_label", "—")),
		str(summary.get("offense_build_label", "—")),
		str(summary.get("three_point_policy_label", "—")),
		str(summary.get("paint_policy_label", "—")),
	]


func _build_defense_text(summary: Dictionary) -> String:
	return "ディフェンス方針: %s\nリバウンド方針: %s\n速攻方針: %s" % [
		str(summary.get("defense_style_label", "—")),
		str(summary.get("rebound_style_label", "—")),
		str(summary.get("transition_style_label", "—")),
	]


func _format_kv_items(items: Array) -> String:
	if items.is_empty():
		return "—"
	var lines: PackedStringArray = PackedStringArray()
	for it in items:
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var m: Dictionary = it as Dictionary
		var lab: String = str(m.get("label", "—"))
		var disp: String = str(m.get("display_value", "—"))
		lines.append("%s: %s" % [lab, disp])
	return "\n".join(lines)


func _bool_ja(v: Variant) -> String:
	if v == null:
		return "—"
	return "はい" if bool(v) else "いいえ"


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


func _on_back_stub_pressed() -> void:
	# 単独プロトタイプ: ホーム遷移は未接続（ボタンは無効化推奨）
	pass
