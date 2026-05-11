extends Control

## ロスター用 JSON の読み込み候補（先頭ほど優先）。Python 生成物は手動配置・gitignore。
var _roster_json_paths: Array[String] = [
	"res://data/roster_from_python.json",
	"res://data/roster_mock.json",
]

const _LOAD_FAILED_MESSAGE := "ロスターデータ読込に失敗しました"

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _last_loaded_uri: String = ""

@onready var _title_label: Label = %TitleLabel
@onready var _team_label: Label = %TeamNameLabel
@onready var _meta_label: Label = %SummaryMetaLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _footer_note_label: Label = %FooterNoteLabel
@onready var _status_label: Label = %StatusLabel
@onready var _row_list: VBoxContainer = %RowList


func _ready() -> void:
	_apply_snapshot(_load_roster_snapshot())


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
		_status_label.visible = true
		_data_source_label.text = ""
		_title_label.text = ""
		_team_label.text = ""
		_meta_label.text = ""
		return

	_status_label.visible = false
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

	_add_table_header_row()
	for item in rows:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		_add_player_row(item as Dictionary)


func _clear_rows() -> void:
	for c in _row_list.get_children():
		c.queue_free()


func _add_table_header_row() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var headers: Array[String] = [
		"#", "選手名", "Pos", "年齢", "OVR", "年俸", "契約", "区分", "状態",
	]
	for i in range(headers.size()):
		var h: String = headers[i]
		var lab := Label.new()
		lab.text = h
		# データ行と同じサイズで、色だけ少し明るくして区別（背景・テーマ追加はしない）
		lab.add_theme_color_override("font_color", Color(0.82, 0.88, 0.96, 1))
		lab.add_theme_font_size_override("font_size", 12)
		lab.custom_minimum_size.x = _col_width(i)
		lab.clip_text = true
		row.add_child(lab)
	_row_list.add_child(row)

	var sep := HSeparator.new()
	_row_list.add_child(sep)


func _col_width(idx: int) -> float:
	# # / 選手名 / Pos / 年齢 / OVR / 年俸 / 契約 / 区分 / 状態（1280幅内・横スクロールなし前提）
	var w: Array[float] = [32.0, 176.0, 36.0, 44.0, 52.0, 106.0, 80.0, 100.0, 136.0]
	if idx >= 0 and idx < w.size():
		return w[idx]
	return 80.0


func _add_player_row(p: Dictionary) -> void:
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
	var con_s := _str_cell(p.get("contract_label", null))
	if con_s == "-":
		con_s = _str_cell(p.get("contract", null))
	var nat_s := _str_cell(p.get("nationality_slot", null))
	var st_s := _str_cell(p.get("status", null))

	var cells: Array[String] = [order_s, name_s, pos_s, age_s, ovr_s, sal_s, con_s, nat_s, st_s]
	for i in range(cells.size()):
		var s: String = cells[i]
		var lab := Label.new()
		lab.text = s
		lab.add_theme_color_override("font_color", Color(0.92, 0.94, 0.98, 1))
		lab.add_theme_font_size_override("font_size", 12)
		lab.custom_minimum_size.x = _col_width(i)
		lab.clip_text = true
		if i == 1:
			# 長い名前が clip されたとき全文を確認できるようにする（autowrap は使わない）
			var name_raw: Variant = p.get("name", null)
			if name_s != "-" and name_raw != null:
				var tip: String = str(name_raw).strip_edges()
				if not tip.is_empty():
					lab.tooltip_text = tip
		row.add_child(lab)
	_row_list.add_child(row)


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
		return "OVR %d" % int(v)
	return "-"


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning("[roster_view] change_scene_to_file failed: %s err=%s" % [_HOME_DASHBOARD_SCENE_PATH, err])
