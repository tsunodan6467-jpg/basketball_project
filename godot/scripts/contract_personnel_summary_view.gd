extends Control

## 契約・人事サマリー閲覧（第10画面・mock 単独確認用）。
## 今回は `contract_personnel_summary_mock.json` のみ読み込む（Python JSON 優先は未実装）。

const _MOCK_JSON_PATH := "res://data/contract_personnel_summary_mock.json"

const _LOAD_FAILED_MESSAGE := "契約・人事情報を読み込めませんでした。mock JSON の配置と UTF-8 を確認してください。"

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _screen_title: Label = %ScreenTitleLabel
@onready var _team_name: Label = %TeamNameLabel
@onready var _league_meta: Label = %LeagueMetaLabel
@onready var _readonly_strip: Label = %ReadonlyStripLabel
@onready var _contract_body: Label = %ContractCardBody
@onready var _risk_rows: VBoxContainer = %RiskRows
@onready var _player_rows: VBoxContainer = %PlayerRows
@onready var _balance_body: Label = %BalanceCardBody
@onready var _caution_body: Label = %CautionCardBody


func _ready() -> void:
	_apply_snapshot(_load_mock_snapshot())


func _load_mock_snapshot() -> Dictionary:
	if not FileAccess.file_exists(_MOCK_JSON_PATH):
		push_warning("[contract_personnel_summary_view] Missing JSON: %s" % _MOCK_JSON_PATH)
		return {"_error": _LOAD_FAILED_MESSAGE}
	var f: FileAccess = FileAccess.open(_MOCK_JSON_PATH, FileAccess.READ)
	if f == null:
		push_warning("[contract_personnel_summary_view] Cannot open: %s" % _MOCK_JSON_PATH)
		return {"_error": _LOAD_FAILED_MESSAGE}
	var text: String = f.get_as_text()
	var parsed: Variant = JSON.parse_string(text)
	if parsed == null:
		push_warning("[contract_personnel_summary_view] JSON parse failed: %s" % _MOCK_JSON_PATH)
		return {"_error": _LOAD_FAILED_MESSAGE}
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("[contract_personnel_summary_view] JSON root is not object: %s" % _MOCK_JSON_PATH)
		return {"_error": _LOAD_FAILED_MESSAGE}
	print("[contract_personnel_summary_view] Loaded mock JSON: ", _MOCK_JSON_PATH)
	return parsed as Dictionary


func _apply_snapshot(d: Dictionary) -> void:
	_clear_vbox(_risk_rows)
	_clear_vbox(_player_rows)

	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_data_source_label.text = ""
		_screen_title.text = ""
		_team_name.text = ""
		_league_meta.text = ""
		_readonly_strip.text = ""
		_contract_body.text = "—"
		_balance_body.text = "—"
		_caution_body.text = ""
		return

	_status_label.visible = false
	_data_source_label.text = "読込元: 同梱 mock JSON / " + _MOCK_JSON_PATH

	_screen_title.text = _txt(d, "screen_title", "契約・人事サマリー（閲覧）")
	var tname: String = _txt(d, "team_name", "—")
	_team_name.text = tname
	var lv_raw: Variant = d.get("league_level", null)
	var lv_s: String = "—"
	if lv_raw != null:
		lv_s = "D%s" % str(lv_raw)
	_league_meta.text = "%s / %s" % [tname, lv_s]

	_readonly_strip.text = "読み取り専用表示（契約更新・交渉・獲得・解雇・FA 操作は行いません）"

	var summary: Dictionary = _dict_or_empty(d.get("summary", {}))
	_contract_body.text = _build_contract_overview_text(summary, _array_or_empty(d.get("contract_items", null)))

	_fill_risk_rows(_array_or_empty(d.get("risk_items", null)))
	_fill_player_rows(_array_or_empty(d.get("player_contract_rows", null)))
	_balance_body.text = _build_balance_text(_array_or_empty(d.get("roster_balance_items", null)))
	_caution_body.text = _build_caution_text(d)


func _clear_vbox(v: VBoxContainer) -> void:
	for c in v.get_children():
		c.queue_free()


func _build_contract_overview_text(summary: Dictionary, items: Array) -> String:
	var lines: PackedStringArray = PackedStringArray()
	lines.append("ロスター: %s 名" % _str_cell(summary.get("roster_count", null)))
	lines.append("年俸合計: %s" % _label_or_raw(summary, "salary_total_label", "salary_total"))
	lines.append("サラリーキャップ: %s" % _label_or_raw(summary, "salary_cap_label", "salary_cap"))
	lines.append("サラリー余力: %s" % _label_or_raw(summary, "salary_cap_room_label", "salary_cap_room"))
	lines.append("平均年俸: %s" % _label_or_raw(summary, "average_salary_label", "average_salary"))
	lines.append("最高年俸: %s" % _label_or_raw(summary, "max_salary_label", "max_salary"))
	lines.append("契約満了予定（目安）: %s 名" % _str_cell(summary.get("expiring_contract_count", null)))
	lines.append("FA 予備軍（fa_shortlist 件数）: %s" % _str_cell(summary.get("fa_candidate_count", null)))
	if summary.get("season_count", null) != null:
		lines.append("セーブ上のシーズン回数: %s" % _str_cell(summary.get("season_count", null)))
	if summary.get("at_annual_menu", null) == true:
		lines.append("年度メニュー直後のセーブの可能性あり。")
	lines.append("")
	lines.append("【契約項目一覧】")
	for it in items:
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = it as Dictionary
		var lab: String = _str_cell(row.get("label", null))
		var disp: String = _str_cell(row.get("display_value", row.get("value", null)))
		var memo: String = _str_cell(row.get("memo", null))
		if memo != "—" and not memo.is_empty():
			lines.append("・%s: %s  (%s)" % [lab, disp, memo])
		else:
			lines.append("・%s: %s" % [lab, disp])
	return "\n".join(lines)


func _label_or_raw(summary: Dictionary, label_key: String, raw_key: String) -> String:
	var lab: Variant = summary.get(label_key, null)
	if lab != null:
		var s: String = str(lab).strip_edges()
		if not s.is_empty():
			return s
	return _str_cell(summary.get(raw_key, null))


func _fill_risk_rows(rows: Array) -> void:
	if rows.is_empty():
		var empty_lab := Label.new()
		empty_lab.text = "（リスク項目がありません）"
		_style_body_label(empty_lab, 12, Color(0.62, 0.66, 0.74, 1))
		_risk_rows.add_child(empty_lab)
		return
	for it in rows:
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = it as Dictionary
		var lab: String = _str_cell(row.get("label", null))
		var disp: String = _str_cell(row.get("display_value", row.get("value", null)))
		var sev: String = _str_cell(row.get("severity", null))
		var memo: String = _str_cell(row.get("memo", null))
		var block := Label.new()
		block.text = "%s\n  表示: %s\n  重要度: %s\n  %s" % [lab, disp, sev, memo]
		_style_body_label(block, 12, Color(0.86, 0.9, 0.95, 1))
		_risk_rows.add_child(block)


func _fill_player_rows(rows: Array) -> void:
	if rows.is_empty():
		var empty_lab := Label.new()
		empty_lab.text = "（選手行がありません）"
		_style_body_label(empty_lab, 12, Color(0.62, 0.66, 0.74, 1))
		_player_rows.add_child(empty_lab)
		return
	var lim: int = mini(rows.size(), 8)
	for i in range(lim):
		var it: Variant = rows[i]
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var p: Dictionary = it as Dictionary
		var nm: String = _str_cell(p.get("player_name", null))
		var pos: String = _str_cell(p.get("position", null))
		var age_s: String = _str_cell(p.get("age", null))
		var ovr: String = _str_cell(p.get("overall", null))
		var pot: String = _str_cell(p.get("potential", null))
		var sal: String = _str_cell(p.get("salary_label", p.get("salary", null)))
		var cy: String = _str_cell(p.get("contract_years_label", p.get("contract_years", null)))
		var nat: String = _str_cell(p.get("nationality_slot_label", p.get("nationality_slot", null)))
		var fa: String = _str_cell(p.get("fa_flag_label", null))
		var rk: String = _str_cell(p.get("risk_label", null))
		var memo: String = _str_cell(p.get("memo", null))
		var line := Label.new()
		line.text = (
			"%s. %s  POS %s  %s歳  OVR%s / POT%s\n"
			+ "  年俸: %s  契約: %s  国籍枠: %s\n"
			+ "  FA 目安: %s  リスク: %s\n"
			+ "  メモ: %s"
		) % [str(p.get("order", i + 1)), nm, pos, age_s, ovr, pot, sal, cy, nat, fa, rk, memo]
		_style_body_label(line, 12, Color(0.86, 0.9, 0.95, 1))
		_player_rows.add_child(line)


func _build_balance_text(items: Array) -> String:
	if items.is_empty():
		return "—"
	var lines: PackedStringArray = PackedStringArray()
	for it in items:
		if typeof(it) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = it as Dictionary
		var lab: String = _str_cell(row.get("label", null))
		var disp: String = _str_cell(row.get("display_value", row.get("value", null)))
		var memo: String = _str_cell(row.get("memo", null))
		if memo != "—" and not memo.is_empty():
			lines.append("%s: %s  (%s)" % [lab, disp, memo])
		else:
			lines.append("%s: %s" % [lab, disp])
	return "\n".join(lines)


func _build_caution_text(d: Dictionary) -> String:
	var parts: PackedStringArray = PackedStringArray()
	parts.append("【読み取り専用】")
	parts.append("契約更新・交渉・獲得・解雇・FA 操作などの UI は含みません。")
	var notes: Array = _array_or_empty(d.get("notes", null))
	for n in notes:
		var s: String = _str_cell(n)
		if s != "—" and not s.is_empty():
			parts.append(s)
	var sec_lines: Array = _section_lines(d, "注意")
	for line in sec_lines:
		var s2: String = str(line).strip_edges()
		if not s2.is_empty():
			parts.append(s2)
	return "\n".join(parts)


func _section_lines(d: Dictionary, title: String) -> Array:
	var out: Array = []
	var sections: Array = _array_or_empty(d.get("sections", null))
	for s in sections:
		if typeof(s) != TYPE_DICTIONARY:
			continue
		var obj: Dictionary = s as Dictionary
		if _str_cell(obj.get("title", null)) != title:
			continue
		var raw_lines: Variant = obj.get("lines", null)
		if typeof(raw_lines) == TYPE_ARRAY:
			return raw_lines as Array
	return out


func _style_body_label(lab: Label, font_px: int, col: Color) -> void:
	lab.autowrap_mode = 2
	lab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	lab.add_theme_font_size_override("font_size", font_px)
	lab.add_theme_color_override("font_color", col)


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
