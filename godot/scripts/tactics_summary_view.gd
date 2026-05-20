extends Control

## 戦術・ローテーションサマリー閲覧（第9画面・読み取り専用）。
## Python 手動配置 JSON を優先し、無ければ同梱モックを読み込む。

var _tactics_summary_json_paths: Array[String] = [
	"res://data/tactics_summary_from_python.json",
	"res://data/tactics_summary_mock.json",
]

const _LOAD_FAILED_MESSAGE := "戦術・ローテーション情報を読み込めませんでした。"

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _last_loaded_uri: String = ""
var _player_role_detail_style_normal: StyleBoxFlat = null
var _player_role_inline_detail_panels: Array = []

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
	_ensure_player_role_inline_detail_styles()
	_apply_snapshot(_load_tactics_summary_snapshot())


func _load_tactics_summary_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _tactics_summary_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f: FileAccess = FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[tactics_summary_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text: String = f.get_as_text()
		var parsed: Variant = JSON.parse_string(text)
		if parsed == null:
			push_warning("[tactics_summary_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[tactics_summary_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data: Dictionary = parsed as Dictionary
		_last_loaded_uri = path
		print("[tactics_summary_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("tactics_summary_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_player_roles()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_set_status_error_visible(true)
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

	_set_status_error_visible(false)
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

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
	_player_role_inline_detail_panels.clear()
	if raw.is_empty():
		var lab := Label.new()
		lab.autowrap_mode = 2
		lab.add_theme_font_size_override("font_size", 13)
		lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		lab.text = "選手ロール情報はありません。"
		_player_roles_body.add_child(lab)
		return
	var roles: Array = []
	for it in raw:
		if roles.size() >= 8:
			break
		if typeof(it) != TYPE_DICTIONARY:
			continue
		roles.append(it as Dictionary)
	var n: int = roles.size()
	for i in range(n):
		var row: Dictionary = roles[i]
		var line := _player_role_line(row)
		var lab := Label.new()
		lab.autowrap_mode = 2
		lab.add_theme_font_size_override("font_size", 13)
		lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		lab.text = line
		lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var detail_btn := Button.new()
		detail_btn.text = "詳細"
		detail_btn.flat = true
		detail_btn.custom_minimum_size = Vector2(36, 0)
		detail_btn.add_theme_font_size_override("font_size", 11)
		var detail_parts: Dictionary = _create_player_role_inline_detail_panel()
		var detail_panel: PanelContainer = detail_parts["panel"] as PanelContainer
		var detail_lab: Label = detail_parts["label"] as Label
		detail_btn.pressed.connect(_on_player_role_detail_button_pressed.bind(detail_panel, detail_lab, row))

		var row_inner := HBoxContainer.new()
		row_inner.add_theme_constant_override("separation", 4)
		row_inner.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row_inner.add_child(lab)
		row_inner.add_child(detail_btn)

		var margin := MarginContainer.new()
		margin.add_theme_constant_override("margin_left", 4)
		margin.add_theme_constant_override("margin_top", 2)
		margin.add_theme_constant_override("margin_right", 4)
		margin.add_theme_constant_override("margin_bottom", 2)
		margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		margin.add_child(row_inner)
		var panel := PanelContainer.new()
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
		panel.add_theme_stylebox_override("panel", row_bg)
		panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		panel.add_child(margin)

		var item_vbox := VBoxContainer.new()
		item_vbox.add_theme_constant_override("separation", 4)
		item_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		item_vbox.add_child(panel)
		item_vbox.add_child(detail_panel)
		_player_roles_body.add_child(item_vbox)
		_player_role_inline_detail_panels.append(detail_panel)
		if i < n - 1:
			_player_roles_body.add_child(HSeparator.new())


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


func _str_cell(v: Variant) -> String:
	if v == null:
		return "—"
	var s: String = str(v).strip_edges()
	return s if not s.is_empty() else "—"


func _make_player_role_detail_panel_style(bg: Color, border: Color) -> StyleBoxFlat:
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


func _ensure_player_role_inline_detail_styles() -> void:
	if _player_role_detail_style_normal != null:
		return
	_player_role_detail_style_normal = _make_player_role_detail_panel_style(
		Color(0.92, 0.96, 1.0, 1),
		Color(0.48, 0.64, 0.86, 1),
	)


func _create_player_role_inline_detail_panel() -> Dictionary:
	_ensure_player_role_inline_detail_styles()
	var detail_panel := PanelContainer.new()
	detail_panel.visible = false
	detail_panel.add_theme_stylebox_override("panel", _player_role_detail_style_normal)
	detail_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var margin := MarginContainer.new()
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var detail_lab := Label.new()
	detail_lab.autowrap_mode = 2
	detail_lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	detail_lab.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	detail_lab.add_theme_font_size_override("font_size", 14)
	detail_lab.add_theme_constant_override("line_spacing", 4)
	detail_lab.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	detail_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	margin.add_child(detail_lab)
	detail_panel.add_child(margin)
	return {"panel": detail_panel, "label": detail_lab}


func _format_player_role_detail_text(row: Dictionary) -> String:
	var nm: String = _str_cell(row.get("player_name", null))
	var pos: String = _str_cell(row.get("position", null))
	var st: String = _str_cell(row.get("starter_label", null))
	var rl: String = _str_cell(row.get("role_label", null))
	var tm: String = _str_cell(row.get("target_minutes_label", null))
	var ord_s: String = _str_cell(row.get("order", null))
	var memo: String = _str_cell(row.get("memo", null))
	return (
		"選手ロール詳細\n"
		+ "%s\n"
		+ "ポジション: %s\n"
		+ "起用: %s\n"
		+ "役割: %s\n"
		+ "目標分数: %s\n"
		+ "順序: %s\n"
		+ "メモ: %s"
	) % [nm, pos, st, rl, tm, ord_s, memo]


func _set_status_error_visible(visible: bool) -> void:
	if not visible:
		_status_label.visible = false
		_status_label.text = ""
		return
	_status_label.add_theme_color_override("font_color", Color(1, 0.52, 0.48, 1))
	_status_label.visible = true


func _on_player_role_detail_button_pressed(
	detail_panel: PanelContainer, detail_lab: Label, row: Dictionary
) -> void:
	if detail_panel.visible:
		detail_panel.visible = false
		return
	for p in _player_role_inline_detail_panels:
		var other: PanelContainer = p as PanelContainer
		if other != detail_panel:
			other.visible = false
	detail_lab.text = _format_player_role_detail_text(row)
	detail_panel.visible = true


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning(
			"[tactics_summary_view] change_scene_to_file failed: %s err=%s"
			% [_HOME_DASHBOARD_SCENE_PATH, err]
		)
