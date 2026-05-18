extends Control

## 財務サマリー閲覧用 JSON（Python 手動配置を優先し、無ければ同梱モック）
var _finance_summary_json_paths: Array[String] = [
	"res://data/finance_summary_from_python.json",
	"res://data/finance_summary_mock.json",
]

const _LOAD_FAILED_MESSAGE := "財務サマリー情報を読み込めませんでした。"

const _HOME_DASHBOARD_SCENE_PATH := "res://scenes/home_dashboard.tscn"

var _last_loaded_uri: String = ""

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _league_meta: Label = %LeagueMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _card_finance_body: Label = %CardFinanceBody
@onready var _card_prior_body: Label = %CardPriorBody
@onready var _card_salary_body: Label = %CardSalaryBody
@onready var _history_body: VBoxContainer = %HistoryBody
@onready var _card_caution_body: Label = %CardCautionBody
@onready var _notes_footer: Label = %NotesFooterLabel


func _ready() -> void:
	_apply_snapshot(_load_finance_summary_snapshot())


func _load_finance_summary_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _finance_summary_json_paths:
		if not FileAccess.file_exists(path):
			continue
		var f: FileAccess = FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[finance_summary_view] Cannot open JSON, trying next: %s" % path)
			continue
		var text: String = f.get_as_text()
		var parsed: Variant = JSON.parse_string(text)
		if parsed == null:
			push_warning("[finance_summary_view] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[finance_summary_view] JSON root is not an object, trying next: %s" % path)
			continue
		var data: Dictionary = parsed as Dictionary
		_last_loaded_uri = path
		print("[finance_summary_view] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("finance_summary_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	_clear_history_body()
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_league_meta.text = ""
		_readonly_strip.text = ""
		_card_finance_body.text = "—"
		_card_prior_body.text = "—"
		_card_salary_body.text = "—"
		_card_caution_body.text = "—"
		_notes_footer.text = ""
		return

	_status_label.visible = false
	_data_source_label.text = _data_source_caption(_last_loaded_uri)

	_screen_title.text = _txt(d, "screen_title", "財務サマリー（閲覧）")
	_team_name.text = _txt(d, "team_name", "—")

	var lv_raw: Variant = d.get("league_level", null)
	var lv_s: String = "—"
	if lv_raw != null:
		lv_s = "D%s" % str(lv_raw)
	_league_meta.text = "%s / %s" % [_txt(d, "team_name", "—"), lv_s]

	_readonly_strip.text = "読み取り専用表示（進行・編集・保存・予算変更は行いません）"

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	_card_finance_body.text = _build_finance_overview_text(summary)
	_card_prior_body.text = _build_prior_season_text(summary)
	_card_salary_body.text = _build_salary_text(summary)
	_fill_history_rows(d.get("history_rows", null))
	_card_caution_body.text = _build_caution_text(d.get("notes", null))

	var notes: Array = _array_or_empty(d.get("notes", null))
	if notes.is_empty():
		_notes_footer.text = "読み取り専用。予算変更・投資・契約更新などの操作は含みません。"
	else:
		_notes_footer.text = _join_note_lines(notes)


func _clear_history_body() -> void:
	for c in _history_body.get_children():
		c.queue_free()


func _build_finance_overview_text(summary: Dictionary) -> String:
	var money: String = _label_or_dash(summary, "money_label", "money")
	var cf: String = _label_or_dash(summary, "cashflow_last_season_label", "cashflow_last_season")
	return "現在資金: %s\n前季収支: %s" % [money, cf]


func _build_prior_season_text(summary: Dictionary) -> String:
	var rev: String = _label_or_dash(summary, "revenue_last_season_label", "revenue_last_season")
	var exp: String = _label_or_dash(summary, "expense_last_season_label", "expense_last_season")
	var cf: String = _label_or_dash(summary, "cashflow_last_season_label", "cashflow_last_season")
	return "前季収入: %s\n前季支出: %s\n前季収支: %s" % [rev, exp, cf]


func _build_salary_text(summary: Dictionary) -> String:
	var cap: String = _label_or_dash(summary, "salary_cap_label", "salary_cap")
	var tot: String = _label_or_dash(summary, "salary_total_label", "salary_total")
	var room: String = _label_or_dash(summary, "salary_cap_room_label", "salary_cap_room")
	return "サラリー上限: %s\n選手年俸合計: %s\nサラリー余力: %s" % [cap, tot, room]


func _label_or_dash(summary: Dictionary, label_key: String, raw_key: String) -> String:
	var lab: Variant = summary.get(label_key, null)
	if lab != null:
		var s: String = str(lab).strip_edges()
		if not s.is_empty():
			return s
	var raw: Variant = summary.get(raw_key, null)
	if raw == null:
		return "—"
	return str(raw).strip_edges() if str(raw).strip_edges() != "" else "—"


func _fill_history_rows(raw: Variant) -> void:
	var rows: Array = _array_or_empty(raw)
	if rows.is_empty():
		var empty_lab := Label.new()
		empty_lab.text = "（履歴がありません）"
		empty_lab.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		empty_lab.add_theme_font_size_override("font_size", 12)
		empty_lab.autowrap_mode = 2
		empty_lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		_history_body.add_child(empty_lab)
		return
	var lim: int = mini(rows.size(), 5)
	for i in range(lim):
		var item: Variant = rows[i]
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = item as Dictionary
		var line := Label.new()
		var season_s: String = _str_cell(row.get("label", row.get("season", null)))
		var rev: String = _str_cell(row.get("revenue_label", row.get("revenue", null)))
		var exp: String = _str_cell(row.get("expense_label", row.get("expense", null)))
		var cf: String = _str_cell(row.get("cashflow_label", row.get("cashflow", null)))
		var memo: String = _str_cell(row.get("memo", null))
		line.text = "%s  収入 %s / 支出 %s / 収支 %s\n   %s" % [season_s, rev, exp, cf, memo]
		line.add_theme_color_override("font_color", Color(0.16, 0.2, 0.3, 1))
		line.add_theme_font_size_override("font_size", 12)
		line.autowrap_mode = 2
		line.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		_history_body.add_child(line)
		if i < lim - 1:
			_history_body.add_child(HSeparator.new())


func _build_caution_text(raw_notes: Variant) -> String:
	var lines: PackedStringArray = PackedStringArray()
	lines.append("読み取り専用です。")
	lines.append("予算変更・投資・契約更新などの操作は未接続です。")
	var arr: Array = _array_or_empty(raw_notes)
	for n in arr:
		var s: String = _str_cell(n)
		if s != "—" and not s.is_empty():
			lines.append(s)
	return "\n".join(lines)


func _join_note_lines(notes: Array) -> String:
	var sb: String = ""
	var first: bool = true
	for n in notes:
		if not first:
			sb += "\n"
		first = false
		sb += _str_cell(n)
	return sb


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
		return "—"
	var s: String = str(v).strip_edges()
	return s if not s.is_empty() else "—"


func _on_home_nav_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_HOME_DASHBOARD_SCENE_PATH)
	if err != OK:
		push_warning(
			"[finance_summary_view] change_scene_to_file failed: %s err=%s"
			% [_HOME_DASHBOARD_SCENE_PATH, err]
		)
