extends Control

## ホーム用 JSON の読み込み候補（先頭ほど優先）。Python 生成物のパスを差し替える場合はここだけ触ればよい。
var _home_json_candidate_paths: Array[String] = [
	"res://data/home_dashboard_from_python.json",
	"res://data/home_dashboard_mock.json",
]

const _LOAD_FAILED_MESSAGE := "データ読込に失敗しました"

@onready var _status_label: Label = %StatusLabel
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
@onready var _next_game: Label = %NextGameLabel
@onready var _club_summary: Label = %ClubSummaryLabel
@onready var _tasks: Label = %TasksLabel
@onready var _news: Label = %NewsLabel


func _ready() -> void:
	_apply_snapshot(_load_home_snapshot())


func _load_home_snapshot() -> Dictionary:
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
		print("[home_dashboard] Loaded JSON from: ", path)
		return data
	return {"_error": _LOAD_FAILED_MESSAGE}


func _apply_snapshot(d: Dictionary) -> void:
	if d.has("_error"):
		_status_label.text = str(d["_error"])
		_status_label.visible = true
		_clear_body()
		return
	_status_label.visible = false
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


func _txt(d: Dictionary, key: String) -> String:
	var v = d.get(key, null)
	if v == null:
		return ""
	return str(v)


func _join_lines(d: Dictionary, key: String, max_lines: int = 0) -> String:
	var raw = d.get(key, null)
	if raw == null or typeof(raw) != TYPE_ARRAY:
		return ""
	var lines: PackedStringArray = PackedStringArray()
	var n := 0
	for item in raw:
		if max_lines > 0 and n >= max_lines:
			break
		lines.append("・" + str(item))
		n += 1
	return "\n".join(lines)


func _set_optional_row(row: HBoxContainer, value_label: Label, text: String) -> void:
	var show := text.strip_edges().length() > 0
	row.visible = show
	if show:
		value_label.text = text
