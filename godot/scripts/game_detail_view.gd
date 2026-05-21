extends Control

## 試合詳細（閲覧）— ReadonlySelectionContext の payload のみ表示。JSON / save / Python なし。

const KIND_GAME := "game"
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


func _selection_context() -> Node:
	return get_node_or_null("/root/ReadonlySelectionContext")


func _apply_from_selection_context() -> void:
	_return_scene = ""
	var ctx := _selection_context()
	if ctx == null:
		_show_unselected("選択状態: ReadonlySelectionContext が見つかりません")
		return

	if not bool(ctx.call("has_selection")):
		_show_unselected("")
		return

	var kind := str(ctx.call("get_kind"))
	if kind != KIND_GAME:
		_show_unselected("")
		return

	var payload_v: Variant = ctx.call("get_payload")
	if typeof(payload_v) != TYPE_DICTIONARY:
		_show_unselected("")
		return
	var payload: Dictionary = payload_v as Dictionary
	if payload.is_empty():
		_show_unselected("")
		return

	_return_scene = str(ctx.call("get_return_scene"))
	_show_game(payload, str(ctx.call("get_source_label")), ctx)


func _show_unselected(extra: String) -> void:
	_title_label.text = "試合詳細（閲覧）"
	_subtitle_label.text = "ReadonlySelectionContext から選択中の試合情報を表示"
	_name_label.text = "選択中の試合情報はありません"
	_meta_label.text = "日程などの一覧画面から試合を選択すると、ここに詳細が表示されます。"
	_clear_detail_rows()
	_add_detail_row("未選択")
	if not extra.is_empty():
		_add_detail_row(extra)
	_data_source_label.text = "選択状態: 未選択"


func _show_game(payload: Dictionary, source_label: String, ctx: Node) -> void:
	var opponent_s := _first_str(payload, ["opponent"], "—")
	var round_s := _first_str(payload, ["round_label", "round"], "—")
	var competition_s := _first_str(payload, ["competition_label", "competition_type"], "—")
	var home_away_s := _first_str(payload, ["home_away"], "—")
	var month_s := _first_str(payload, ["month_label"], "—")
	var detail_s := _first_str(payload, ["detail"], "—")
	var label_s := _first_str(payload, ["label"], "—")
	var source_s := source_label.strip_edges()
	if source_s.is_empty():
		source_s = "不明"

	_title_label.text = "試合詳細（閲覧）"
	_subtitle_label.text = "ReadonlySelectionContext から選択中の試合情報を表示"
	_name_label.text = opponent_s
	_meta_label.text = "%s ・ %s ・ %s" % [round_s, competition_s, home_away_s]

	_clear_detail_rows()
	_add_detail_row("対戦: %s" % opponent_s)
	_add_detail_row("ラウンド: %s" % round_s)
	_add_detail_row("大会: %s" % competition_s)
	_add_detail_row("ホーム/アウェイ: %s" % home_away_s)
	_add_detail_row("月表示: %s" % month_s)
	_add_detail_row("詳細: %s" % detail_s)
	_add_detail_row("ラベル: %s" % label_s)
	_add_detail_row("参照元: %s" % source_s)

	if OS.is_debug_build() and ctx != null:
		var eid := str(ctx.call("get_event_id")).strip_edges()
		if not eid.is_empty():
			var dbg := Label.new()
			dbg.text = "debug event_id: %s" % eid
			dbg.add_theme_font_size_override("font_size", 10)
			dbg.add_theme_color_override("font_color", Color(0.45, 0.5, 0.58, 1))
			dbg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			_detail_rows.add_child(dbg)

	_data_source_label.text = "選択状態: 試合（参照元: %s）" % source_s


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


func _on_back_button_pressed() -> void:
	if _return_scene.is_empty():
		_data_source_label.text = "戻り先がありません"
		return
	var ctx := _selection_context()
	if ctx != null:
		ctx.call("clear")
	var err := get_tree().change_scene_to_file(_return_scene)
	if err != OK:
		push_warning(
			"[game_detail_view] change_scene_to_file failed: %s err=%s"
			% [_return_scene, err]
		)


func _on_home_nav_button_pressed() -> void:
	var ctx := _selection_context()
	if ctx != null:
		ctx.call("clear")
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning(
			"[game_detail_view] change_scene_to_file failed: %s err=%s"
			% [_HOME_DASHBOARD_SCENE_PATH, err]
		)
