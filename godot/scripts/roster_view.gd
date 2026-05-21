extends Control

## ロスター用 JSON の読み込み候補（先頭ほど優先）。Python 生成物は手動配置・gitignore。
var _roster_json_paths: Array[String] = [
	"res://data/roster_from_python.json",
	"res://data/roster_mock.json",
]

const _LOAD_FAILED_MESSAGE := "ロスターデータ読込に失敗しました"

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"
const _PLAYER_DETAIL_VIEW_SCENE_PATH := "res://scenes/player_detail_view.tscn"
const _ROSTER_VIEW_SCENE_PATH := "res://scenes/roster_view.tscn"

var _last_loaded_uri: String = ""
var _summary_panel: PanelContainer = null
var _summary_style_normal: StyleBoxFlat = null
var _summary_style_error: StyleBoxFlat = null

@onready var _title_label: Label = %TitleLabel
@onready var _team_label: Label = %TeamNameLabel
@onready var _meta_label: Label = %SummaryMetaLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _footer_note_label: Label = %FooterNoteLabel
@onready var _status_label: Label = %StatusLabel
@onready var _row_list: VBoxContainer = %RowList
@onready var _scroll: ScrollContainer = $Margin/RootCol/Scroll


func _ready() -> void:
	_setup_selected_player_summary_style()
	_apply_snapshot(_load_roster_snapshot())
	_queue_restore_return_scroll()


func _selection_context() -> Node:
	return get_node_or_null("/root/ReadonlySelectionContext")


func _load_roster_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _roster_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f := FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[roster_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text := f.get_as_text()
		var parsed = JSON.parse_string(text)
		if parsed == null:
			push_warning("[roster_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[roster_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data := parsed as Dictionary
		_last_loaded_uri = path
		print("[roster_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("roster_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_rows()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_set_selected_player_summary_visible(true, true)
		_data_source_label.text = ""
		_title_label.text = ""
		_team_label.text = ""
		_meta_label.text = ""
		return

	_set_selected_player_summary_visible(false)
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_title_label.text = _txt(d, "screen_title", "ロスター（閲覧）")
	_team_label.text = _txt(d, "team_name", "自クラブ")

	var lv = d.get("league_level", null)
	var lv_s := "-"
	if lv != null:
		lv_s = str(lv)

	var summary := _dict_or_empty(d.get("summary", {}))
	var rc := _int_or(summary.get("roster_count", null), -1)
	var dom := _int_or(summary.get("domestic_count", null), -1)
	var fr := _int_or(summary.get("foreign_count", null), -1)
	var asia := _int_or(summary.get("asia_or_naturalized_count", null), -1)
	if rc >= 0 and dom >= 0 and fr >= 0 and asia >= 0:
		_meta_label.text = "所属: D%s ／ 登録 %d 名（国内 %d / 外国籍 %d / アジア・帰化 %d）" % [
			lv_s, rc, dom, fr, asia,
		]
	elif rc >= 0:
		_meta_label.text = "所属: D%s ／ 登録 %d 名" % [lv_s, rc]
	else:
		_meta_label.text = "所属: D%s ／ 登録人数 不明" % lv_s

	_footer_note_label.text = "読み取り専用です。契約・移籍・起用変更などの操作は行いません（未接続）。"

	var players_raw = d.get("players", null)
	var rows: Array = []
	if typeof(players_raw) == TYPE_ARRAY:
		rows = players_raw as Array

	var valid_players: Array = []
	for item in rows:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		valid_players.append(item as Dictionary)

	_add_table_header_row()
	var n := valid_players.size()
	for i in range(n):
		_add_player_row(valid_players[i] as Dictionary)
		if i < n - 1:
			_row_list.add_child(HSeparator.new())


func _clear_rows() -> void:
	for c in _row_list.get_children():
		c.queue_free()


## 表ヘッダー用。白カード向け `Phase4TableHead`（`roster_view.tscn` ルートの Theme 継承）。
## Theme 既定フォントは 11px のため、従来表示との互換で 12px を維持する。
func _style_ondark_table_header_label(lab: Label) -> void:
	lab.theme_type_variation = &"Phase4TableHead"
	lab.add_theme_font_size_override("font_size", 12)


## 表セル用。白カード向け `Phase4TableCell`（同上）。
func _style_ondark_table_cell_label(lab: Label) -> void:
	lab.theme_type_variation = &"Phase4TableCell"
	lab.add_theme_font_size_override("font_size", 12)


func _add_table_header_row() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var headers: Array[String] = [
		"#", "選手名", "Pos", "年齢", "OVR", "年俸", "残り契約", "区分", "状態",
	]
	for i in range(headers.size()):
		var h: String = headers[i]
		var lab := Label.new()
		lab.text = h
		_style_ondark_table_header_label(lab)
		lab.custom_minimum_size.x = _col_width(i)
		lab.clip_text = true
		row.add_child(lab)
	_row_list.add_child(row)

	var sep := HSeparator.new()
	_row_list.add_child(sep)


func _col_width(idx: int) -> float:
	# # / 選手名 / Pos / 年齢 / OVR / 年俸 / 残り契約 / 区分 / 状態（1280幅内・横スクロールなし前提）
	var w: Array[float] = [32.0, 176.0, 36.0, 44.0, 52.0, 106.0, 80.0, 100.0, 136.0]
	if idx >= 0 and idx < w.size():
		return w[idx]
	return 80.0


func _add_player_row(p: Dictionary) -> void:
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

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)

	var order_s := _order_cell(p.get("order", null))
	var name_s := _str_cell(p.get("name", null))
	var pos_s := _str_cell(p.get("position", null))
	var age_s := _age_cell(p.get("age", null))
	var ovr_s := _ovr_cell(p.get("ovr", null))
	var sal_s := _str_cell(p.get("salary_label", null))
	if sal_s == "-":
		sal_s = _str_cell(p.get("salary", null))
	var con_s := _contract_cell(p)
	var nat_s := _str_cell(p.get("nationality_slot", null))
	var st_s := _str_cell(p.get("status", null))

	var cells: Array[String] = [order_s, name_s, pos_s, age_s, ovr_s, sal_s, con_s, nat_s, st_s]
	for i in range(cells.size()):
		var s: String = cells[i]
		if i == 1:
			var name_cell := HBoxContainer.new()
			name_cell.add_theme_constant_override("separation", 4)
			name_cell.custom_minimum_size.x = _col_width(1)

			var lab := Label.new()
			lab.text = s
			_style_ondark_table_cell_label(lab)
			lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			lab.clip_text = true
			lab.add_theme_font_size_override("font_size", 13)
			lab.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
			var name_raw: Variant = p.get("name", null)
			if name_s != "-" and name_raw != null:
				var tip: String = str(name_raw).strip_edges()
				if not tip.is_empty():
					lab.tooltip_text = tip
					lab.mouse_filter = Control.MOUSE_FILTER_PASS

			var detail_btn := Button.new()
			detail_btn.text = "詳細"
			detail_btn.flat = true
			detail_btn.custom_minimum_size = Vector2(36, 0)
			detail_btn.add_theme_font_size_override("font_size", 11)
			detail_btn.pressed.connect(_show_selected_player_summary.bind(p))

			var screen_btn := Button.new()
			screen_btn.text = "画面"
			screen_btn.flat = true
			screen_btn.custom_minimum_size = Vector2(32, 0)
			screen_btn.add_theme_font_size_override("font_size", 11)
			screen_btn.pressed.connect(_open_player_detail_view.bind(p))

			name_cell.add_child(lab)
			name_cell.add_child(detail_btn)
			name_cell.add_child(screen_btn)
			row.add_child(name_cell)
			continue

		var lab := Label.new()
		lab.text = s
		_style_ondark_table_cell_label(lab)
		lab.custom_minimum_size.x = _col_width(i)
		lab.clip_text = true
		if i == 5:
			lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		if i == 4:
			lab.add_theme_font_size_override("font_size", 13)
			lab.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
		elif i == 8:
			lab.add_theme_font_size_override("font_size", 13)
			lab.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
		if i == 8 and st_s != "-":
			# 状態列が clip されたとき全文を確認できるようにする（表示文字と同じ）
			lab.tooltip_text = st_s
			lab.mouse_filter = Control.MOUSE_FILTER_PASS
		if i == 6 and con_s != "-":
			# 残り契約列が clip されたとき contract_label 等の補足全文を確認できる（表示は _contract_cell のまま）
			var con_tip: String = ""
			var cl_raw: Variant = p.get("contract_label", null)
			if cl_raw != null:
				con_tip = str(cl_raw).strip_edges()
			if con_tip.is_empty():
				var cy_raw: Variant = p.get("contract_years_left", null)
				if cy_raw != null:
					if typeof(cy_raw) in [TYPE_INT, TYPE_FLOAT]:
						var cn: int = int(cy_raw)
						if cn >= 0:
							con_tip = "残り%d年" % cn
					elif typeof(cy_raw) == TYPE_STRING:
						var cys: String = str(cy_raw).strip_edges()
						if cys.is_valid_int():
							var cni: int = cys.to_int()
							if cni >= 0:
								con_tip = "残り%d年" % cni
			if con_tip.is_empty():
				var co_raw: Variant = p.get("contract", null)
				if co_raw != null:
					var co_tip: String = str(co_raw).strip_edges()
					if not co_tip.is_empty():
						con_tip = co_tip
			if not con_tip.is_empty():
				lab.tooltip_text = con_tip
				lab.mouse_filter = Control.MOUSE_FILTER_PASS
		row.add_child(lab)
	panel.add_child(row)
	_row_list.add_child(panel)


func _dict_or_empty(v: Variant) -> Dictionary:
	if typeof(v) == TYPE_DICTIONARY:
		return v as Dictionary
	return {}


func _int_or(v: Variant, default_neg: int) -> int:
	if v == null:
		return default_neg
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		return int(v)
	if typeof(v) == TYPE_STRING:
		if str(v).strip_edges().is_empty():
			return default_neg
		return int(str(v).to_float())
	return default_neg


func _txt(d: Dictionary, key: String, fallback: String) -> String:
	var v = d.get(key, null)
	if v == null:
		return fallback
	var s := str(v).strip_edges()
	return s if not s.is_empty() else fallback


func _str_cell(v: Variant) -> String:
	if v == null:
		return "-"
	var s := str(v).strip_edges()
	return s if not s.is_empty() else "-"


func _order_cell(v: Variant) -> String:
	## JSON パース後に order が float になる環境でも「1.0」表記を避け、整数として表示する。
	if v == null:
		return "-"
	if typeof(v) == TYPE_INT:
		return str(v)
	if typeof(v) == TYPE_FLOAT:
		return str(int(v))
	if typeof(v) == TYPE_STRING:
		var st := str(v).strip_edges()
		if st.is_empty():
			return "-"
		if st.is_valid_int():
			return str(st.to_int())
		if st.is_valid_float():
			return str(int(st.to_float()))
		return "-"
	return "-"


func _age_cell(v: Variant) -> String:
	if v == null:
		return "-"
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		return "%d歳" % int(v)
	var s := str(v).strip_edges()
	return s if not s.is_empty() else "-"


func _ovr_cell(v: Variant) -> String:
	if v == null:
		return "-"
	if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
		return str(int(v))
	return "-"


func _contract_cell(p: Dictionary) -> String:
	## contract_years_left を優先し、無ければ contract_label / contract を「N年」表記に寄せる（DTOは変更しない）。
	var cy: Variant = p.get("contract_years_left", null)
	if cy != null:
		if typeof(cy) in [TYPE_INT, TYPE_FLOAT]:
			var n: int = int(cy)
			if n >= 0:
				return "%d年" % n
		elif typeof(cy) == TYPE_STRING:
			var cys: String = str(cy).strip_edges()
			if cys.is_valid_int():
				var ni: int = cys.to_int()
				if ni >= 0:
					return "%d年" % ni

	var lab_s := _str_cell(p.get("contract_label", null))
	if lab_s == "-":
		lab_s = _str_cell(p.get("contract", null))
	if lab_s == "-" or lab_s.is_empty():
		return "-"
	var display: String = lab_s.strip_edges().trim_prefix("残り").strip_edges()
	if display.is_empty():
		return "-"
	return display


func _make_summary_panel_style(bg: Color, border: Color) -> StyleBoxFlat:
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


func _setup_selected_player_summary_style() -> void:
	if _summary_panel != null:
		return

	_summary_style_normal = _make_summary_panel_style(
		Color(0.92, 0.96, 1.0, 1),
		Color(0.48, 0.64, 0.86, 1),
	)
	_summary_style_error = _make_summary_panel_style(
		Color(1.0, 0.94, 0.94, 1),
		Color(0.86, 0.48, 0.48, 1),
	)

	var parent := _status_label.get_parent()
	var idx := _status_label.get_index()

	_summary_panel = PanelContainer.new()
	_summary_panel.add_theme_stylebox_override("panel", _summary_style_normal)
	_summary_panel.visible = false
	_summary_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var margin := MarginContainer.new()
	parent.remove_child(_status_label)
	margin.add_child(_status_label)
	_summary_panel.add_child(margin)
	parent.add_child(_summary_panel)
	parent.move_child(_summary_panel, idx)

	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_status_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	_status_label.add_theme_font_size_override("font_size", 14)
	_status_label.add_theme_constant_override("line_spacing", 4)
	_status_label.add_theme_color_override("font_color", Color(0.08, 0.11, 0.18, 1))
	_status_label.visible = true


func _set_selected_player_summary_visible(visible: bool, is_error: bool = false) -> void:
	if _summary_panel == null:
		_status_label.visible = visible
		if not visible:
			_status_label.text = ""
		return

	if not visible:
		_summary_panel.visible = false
		_status_label.text = ""
		return

	_summary_panel.add_theme_stylebox_override(
		"panel",
		_summary_style_error if is_error else _summary_style_normal,
	)
	_status_label.add_theme_color_override(
		"font_color",
		Color(1, 0.52, 0.48, 1) if is_error else Color(0.08, 0.11, 0.18, 1),
	)
	_summary_panel.visible = true
	_status_label.visible = true


func _show_selected_player_summary(p: Dictionary) -> void:
	var name_s := _str_cell(p.get("name", null))
	var pos_s := _str_cell(p.get("position", null))
	var age_s := _age_cell(p.get("age", null))
	var ovr_s := _ovr_cell(p.get("ovr", null))
	var st_s := _str_cell(p.get("status", null))

	var con_s := "-"
	var cl_raw: Variant = p.get("contract_label", null)
	if cl_raw != null:
		var cl_tip: String = str(cl_raw).strip_edges()
		if not cl_tip.is_empty():
			con_s = cl_tip
	if con_s == "-":
		var cy_raw: Variant = p.get("contract_years_left", null)
		if cy_raw != null:
			if typeof(cy_raw) in [TYPE_INT, TYPE_FLOAT]:
				var cn: int = int(cy_raw)
				if cn >= 0:
					con_s = "残り%d年" % cn
			elif typeof(cy_raw) == TYPE_STRING:
				var cys: String = str(cy_raw).strip_edges()
				if cys.is_valid_int():
					var cni: int = cys.to_int()
					if cni >= 0:
						con_s = "残り%d年" % cni
	if con_s == "-":
		var cell_con := _contract_cell(p)
		if cell_con != "-":
			con_s = cell_con

	_status_label.text = "%s\n%s / %s\nOVR %s\n契約: %s\n状態: %s" % [
		name_s, pos_s, age_s, ovr_s, con_s, st_s,
	]
	_set_selected_player_summary_visible(true, false)


func _player_id_from_row(player_row: Dictionary) -> int:
	var raw: Variant = player_row.get("player_id", -1)
	if raw == null:
		return -1
	if typeof(raw) in [TYPE_INT, TYPE_FLOAT]:
		return int(raw)
	if typeof(raw) == TYPE_STRING:
		var s := str(raw).strip_edges()
		if s.is_valid_int():
			return s.to_int()
	return -1


func _show_roster_status_message(message: String, is_error: bool = true) -> void:
	_status_label.text = message
	_set_selected_player_summary_visible(true, is_error)


func _open_player_detail_view(player_row: Dictionary) -> void:
	var player_id := _player_id_from_row(player_row)
	if player_id <= 0:
		_show_roster_status_message("選手詳細画面を開けません: player_id がありません", true)
		return

	var ctx := _selection_context()
	if ctx == null:
		_show_roster_status_message("選択状態を保存できません", true)
		return

	ctx.call(
		"set_return_state",
		_ROSTER_VIEW_SCENE_PATH,
		{
			"scroll_vertical": _current_scroll_vertical(),
			"source": "roster",
			"target_kind": "player",
			"target_id": player_id,
		},
	)

	var payload := player_row.duplicate()
	if not payload.has("player_id"):
		payload["player_id"] = player_id

	ctx.call("set_player", player_id, payload, _ROSTER_VIEW_SCENE_PATH, "ロスター")

	var err := get_tree().change_scene_to_file(_PLAYER_DETAIL_VIEW_SCENE_PATH)
	if err != OK:
		_show_roster_status_message("選手詳細画面を開けませんでした", true)
		push_warning(
			"[roster_view] change_scene_to_file failed: %s err=%s"
			% [_PLAYER_DETAIL_VIEW_SCENE_PATH, err]
		)


func _queue_restore_return_scroll() -> void:
	call_deferred("_restore_return_scroll")


func _restore_return_scroll() -> void:
	var ctx := _selection_context()
	if ctx == null:
		return
	var state_v: Variant = ctx.call("consume_return_state", _ROSTER_VIEW_SCENE_PATH)
	if typeof(state_v) != TYPE_DICTIONARY:
		return
	var state: Dictionary = state_v as Dictionary
	if state.is_empty():
		return
	var scroll_y := _int_or(state.get("scroll_vertical", null), -1)
	if scroll_y < 0:
		return
	if _scroll == null:
		return
	_scroll.scroll_vertical = scroll_y


func _current_scroll_vertical() -> int:
	if _scroll == null:
		return 0
	return int(_scroll.scroll_vertical)


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning("[roster_view] change_scene_to_file failed: %s err=%s" % [_HOME_DASHBOARD_SCENE_PATH, err])
