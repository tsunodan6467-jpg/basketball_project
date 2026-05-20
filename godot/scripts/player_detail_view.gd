extends Control

## 選手詳細（閲覧）— ReadonlySelectionContext の payload のみ表示。JSON / save / Python なし。

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _return_scene: String = ""

@onready var _title_label: Label = %TitleLabel
@onready var _subtitle_label: Label = %SubTitleLabel
@onready var _name_label: Label = %NameLabel
@onready var _meta_label: Label = %MetaLabel
@onready var _detail_rows: VBoxContainer = %DetailRows
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _footer_note_label: Label = %FooterNoteLabel
@onready var _back_button: Button = %BackButton
@onready var _home_nav_button: Button = %HomeNavButton


func _ready() -> void:
	_footer_note_label.text = "読み取り専用。進行・編集・保存は行いません。Python 自動起動は行いません。"
	_apply_from_selection_context()


func _apply_from_selection_context() -> void:
	_return_scene = ""
	if not _context_available():
		_show_unselected("Autoload が利用できません")
		return

	var ctx := ReadonlySelectionContext
	if not ctx.has_selection() or ctx.get_kind() != ctx.KIND_PLAYER:
		_show_unselected("")
		return

	var payload: Dictionary = ctx.get_payload()
	if payload.is_empty():
		_show_unselected("")
		return

	_return_scene = ctx.get_return_scene()
	_show_player(payload, ctx.get_source_label())


func _context_available() -> bool:
	return get_node_or_null("/root/ReadonlySelectionContext") != null


func _show_unselected(extra: String) -> void:
	_title_label.text = "選手詳細（閲覧）"
	_subtitle_label.text = "ReadonlySelectionContext から選択中の選手情報を表示"
	_name_label.text = "選択中の選手情報はありません"
	_meta_label.text = "ロスターなどの一覧画面から選手を選択すると、ここに詳細が表示されます。"
	_clear_detail_rows()
	_add_detail_row("未選択")
	if not extra.is_empty():
		_add_detail_row(extra)
	_data_source_label.text = "選択状態: 未選択"


func _show_player(payload: Dictionary, source_label: String) -> void:
	var name_s := _first_str(payload, ["name", "player_name"], "—")
	var pos_s := _first_str(payload, ["position", "pos"], "—")
	var age_s := _format_age(payload.get("age", null))
	var ovr_s := _first_str(payload, ["overall", "ovr"], "—")
	var pot_s := _first_str(payload, ["potential", "pot"], "—")
	var contract_s := _format_contract(payload)
	var status_s := _first_str(
		payload,
		["status", "status_label", "condition_label"],
		"—",
	)
	var nat_s := _first_str(
		payload,
		["nationality_slot_label", "nationality_slot", "nationality"],
		"—",
	)
	var source_s := source_label.strip_edges()
	if source_s.is_empty():
		source_s = "不明"

	_title_label.text = "選手詳細（閲覧）"
	_subtitle_label.text = "ReadonlySelectionContext から選択中の選手情報を表示"
	_name_label.text = name_s
	_meta_label.text = "%s ・ %s" % [pos_s, age_s]

	_clear_detail_rows()
	_add_detail_row("氏名: %s" % name_s)
	_add_detail_row("ポジション: %s" % pos_s)
	_add_detail_row("年齢: %s" % age_s)
	_add_detail_row("OVR: %s" % ovr_s)
	_add_detail_row("POT: %s" % pot_s)
	_add_detail_row("契約: %s" % contract_s)
	_add_detail_row("状態: %s" % status_s)
	_add_detail_row("国籍枠: %s" % nat_s)
	_add_detail_row("参照元: %s" % source_s)

	if OS.is_debug_build():
		var pid := ReadonlySelectionContext.get_player_id()
		if pid >= 0:
			var dbg := Label.new()
			dbg.text = "debug player_id: %d" % pid
			dbg.add_theme_font_size_override("font_size", 10)
			dbg.add_theme_color_override("font_color", Color(0.45, 0.5, 0.58, 1))
			dbg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			_detail_rows.add_child(dbg)

	_data_source_label.text = "選択状態: 選手（参照元: %s）" % source_s


func _clear_detail_rows() -> void:
	for child in _detail_rows.get_children():
		_detail_rows.remove_child(child)
		child.free()


func _add_detail_row(line: String) -> void:
	var lbl := Label.new()
	lbl.text = line
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl.add_theme_font_size_override("font_size", 14)
	lbl.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	_detail_rows.add_child(lbl)


func _first_str(payload: Dictionary, keys: Array, fallback: String) -> String:
	for key in keys:
		if not payload.has(key):
			continue
		var cell := _str_cell(payload.get(key, null))
		if cell != "-":
			return cell
	return fallback


func _str_cell(v: Variant) -> String:
	if v == null:
		return "-"
	var s := str(v).strip_edges()
	return s if not s.is_empty() else "-"


func _format_age(v: Variant) -> String:
	if v == null:
		return "—"
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		return "%d歳" % int(v)
	var s := str(v).strip_edges()
	return s if not s.is_empty() else "—"


func _format_contract(payload: Dictionary) -> String:
	for key in ["contract_label", "contract_years_label", "contract"]:
		if payload.has(key):
			var cell := _str_cell(payload.get(key, null))
			if cell != "-":
				return cell
	var cy: Variant = payload.get("contract_years_left", null)
	if cy != null:
		if typeof(cy) in [TYPE_INT, TYPE_FLOAT]:
			var n: int = int(cy)
			if n >= 0:
				return "残り%d年" % n
		elif typeof(cy) == TYPE_STRING:
			var cys: String = str(cy).strip_edges()
			if cys.is_valid_int():
				var ni: int = cys.to_int()
				if ni >= 0:
					return "残り%d年" % ni
	return "—"


func _on_back_button_pressed() -> void:
	if _return_scene.is_empty():
		_data_source_label.text = "戻り先がありません"
		return
	if _context_available():
		ReadonlySelectionContext.clear()
	var err := get_tree().change_scene_to_file(_return_scene)
	if err != OK:
		push_warning(
			"[player_detail_view] change_scene_to_file failed: %s err=%s"
			% [_return_scene, err]
		)


func _on_home_nav_button_pressed() -> void:
	if _context_available():
		ReadonlySelectionContext.clear()
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning(
			"[player_detail_view] change_scene_to_file failed: %s err=%s"
			% [_HOME_DASHBOARD_SCENE_PATH, err]
		)
