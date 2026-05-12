extends Control

## ホーム用 JSON の読み込み候補（先頭ほど優先）。Python 生成物のパスを差し替える場合はここだけ触ればよい。
var _home_json_candidate_paths: Array[String] = [
	"res://data/home_dashboard_from_python.json",
	"res://data/home_dashboard_mock.json",
]

const _LOAD_FAILED_MESSAGE := "データ読込に失敗しました"

const _ROSTER_VIEW_SCENE_PATH := "res://scenes/roster_view.tscn"
const _CLUB_HISTORY_VIEW_SCENE_PATH := "res://scenes/club_history_view.tscn"
const _STANDINGS_VIEW_SCENE_PATH := "res://scenes/standings_view.tscn"
const _SCHEDULE_VIEW_SCENE_PATH := "res://scenes/schedule_view.tscn"

## 直近で読み取りに成功した `res://` パス（表示用）
var _last_loaded_uri: String = ""

@onready var _status_label: Label = %StatusLabel
@onready var _data_source_label: Label = %DataSourceLabel
@onready var _club_name: Label = %ClubNameLabel
@onready var _season: Label = %SeasonLabel
@onready var _division: Label = %DivisionLabel
@onready var _rank_record: Label = %RankRecordLabel
@onready var _money: Label = %MoneyLabel
@onready var _owner_trust: Label = %OwnerTrustLabel
@onready var _owner_row: HBoxContainer = %OwnerTrustRow
@onready var _salary_cap: Label = %SalaryCapLabel
@onready var _salary_row: HBoxContainer = %SalaryCapRow
@onready var _recent_form: Label = %RecentFormLabel
@onready var _recent_row: HBoxContainer = %RecentFormRow
@onready var _warnings: Label = %WarningsLabel
@onready var _warnings_row: HBoxContainer = %WarningsRow
@onready var _warnings_card: PanelContainer = %CardWarnings
@onready var _extras_card: PanelContainer = %CardTeamExtras
@onready var _next_game: Label = %NextGameLabel
@onready var _club_summary: Label = %ClubSummaryLabel
@onready var _tasks: Label = %TasksLabel
@onready var _news: Label = %NewsLabel


func _ready() -> void:
	_apply_snapshot(_load_home_snapshot())


func _load_home_snapshot() -> Dictionary:
	_last_loaded_uri = ""
	for path in _home_json_candidate_paths:
		if not FileAccess.file_exists(path):
			continue
		var f := FileAccess.open(path, FileAccess.READ)
		if f == null:
			push_warning("[home_dashboard] Cannot open JSON, trying next: %s" % path)
			continue
		var text := f.get_as_text()
		var parsed = JSON.parse_string(text)
		if parsed == null:
			push_warning("[home_dashboard] JSON parse failed, trying next: %s" % path)
			continue
		if typeof(parsed) != TYPE_DICTIONARY:
			push_warning("[home_dashboard] JSON root is not an object, trying next: %s" % path)
			continue
		var data := parsed as Dictionary
		_last_loaded_uri = path
		print("[home_dashboard] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _data_source_caption(uri: String) -> String:
	if uri.is_empty():
		return ""
	if uri.ends_with("home_dashboard_from_python.json"):
		return "読込元: Python生成JSON（手動配置・優先） / " + uri
	return "読込元: 同梱モックJSON / " + uri


func _apply_snapshot(d: Dictionary) -> void:
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_data_source_label.text = ""
		_clear_body()
		return
	_status_label.visible = false
	_data_source_label.text = _data_source_caption(_last_loaded_uri)
	_club_name.text = _txt(d, "club_name")
	_season.text = _txt(d, "season_label")
	_division.text = _txt(d, "division")
	_rank_record.text = _txt(d, "rank_record")
	_money.text = _txt(d, "money")
	_next_game.text = _txt(d, "next_game")
	_club_summary.text = _join_lines(d, "club_summary")
	_tasks.text = _join_lines(d, "tasks", 3)
	_news.text = _join_lines(d, "news")
	_set_optional_row(_owner_row, _owner_trust, _txt(d, "owner_trust"))
	_set_optional_row(_salary_row, _salary_cap, _txt(d, "salary_cap"))
	_set_optional_row(_recent_row, _recent_form, _txt(d, "recent_form"))
	_set_optional_row(_warnings_row, _warnings, _txt(d, "warnings"))
	_extras_card.visible = _owner_row.visible or _salary_row.visible or _recent_row.visible
	_warnings_card.visible = _warnings_row.visible


func _clear_body() -> void:
	_club_name.text = ""
	_season.text = ""
	_division.text = ""
	_rank_record.text = ""
	_money.text = ""
	_next_game.text = ""
	_club_summary.text = ""
	_tasks.text = ""
	_news.text = ""
	_owner_row.visible = false
	_salary_row.visible = false
	_recent_row.visible = false
	_warnings_row.visible = false
	_extras_card.visible = false
	_warnings_card.visible = false


func _txt(d: Dictionary, key: String) -> String:
	var v = d.get(key, null)
	if v == null:
		return ""
	return str(v)


func _join_lines(d: Dictionary, key: String, max_lines: int = 0) -> String:
	var raw = d.get(key, null)
	if raw == null or typeof(raw) != TYPE_ARRAY:
		return ""
	var acc := ""
	var n := 0
	for item in raw:
		if max_lines > 0 and n >= max_lines:
			break
		if acc.length() > 0:
			acc += "\n"
		acc += "・" + str(item)
		n += 1
	return acc


func _set_optional_row(row: HBoxContainer, value_label: Label, text: String) -> void:
	var show := text.strip_edges().length() > 0
	row.visible = show
	if show:
		value_label.text = text


func _on_roster_view_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_ROSTER_VIEW_SCENE_PATH)
	if err != OK:
		push_warning("[home_dashboard] change_scene_to_file failed: %s err=%s" % [_ROSTER_VIEW_SCENE_PATH, err])


func _on_club_history_view_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_CLUB_HISTORY_VIEW_SCENE_PATH)
	if err != OK:
		push_warning("[home_dashboard] change_scene_to_file failed: %s err=%s" % [_CLUB_HISTORY_VIEW_SCENE_PATH, err])


func _on_standings_view_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_STANDINGS_VIEW_SCENE_PATH)
	if err != OK:
		push_warning("[home_dashboard] change_scene_to_file failed: %s err=%s" % [_STANDINGS_VIEW_SCENE_PATH, err])


func _on_schedule_view_button_pressed() -> void:
	# 閲覧専用: シーン切替のみ。Python 起動・save・ゲーム進行は行わない。
	var err := get_tree().change_scene_to_file(_SCHEDULE_VIEW_SCENE_PATH)
	if err != OK:
		push_warning("[home_dashboard] change_scene_to_file failed: %s err=%s" % [_SCHEDULE_VIEW_SCENE_PATH, err])
