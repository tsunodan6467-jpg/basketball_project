extends Node

## 読み取り専用詳細画面へ渡す選択状態（セーブ・Python・JSON書込なし）。

const KIND_PLAYER := "player"
const KIND_GAME := "game"

var _kind: String = ""
var _payload: Dictionary = {}
var _return_scene: String = ""
var _source_label: String = ""
var _player_id: int = -1
var _event_id: String = ""


func set_selection(
	kind: String,
	payload: Dictionary,
	return_scene: String = "",
	source_label: String = ""
) -> void:
	var player_id := -1
	var event_id := ""
	if kind == KIND_PLAYER and payload.has("player_id"):
		player_id = int(payload["player_id"])
	if kind == KIND_GAME and payload.has("event_id"):
		event_id = str(payload["event_id"])
	_apply_selection(kind, payload, return_scene, source_label, player_id, event_id)


func set_player(
	player_id: int,
	payload: Dictionary,
	return_scene: String = "",
	source_label: String = ""
) -> void:
	var copy := payload.duplicate()
	if not copy.has("player_id"):
		copy["player_id"] = player_id
	_apply_selection(KIND_PLAYER, copy, return_scene, source_label, player_id, "")


func set_game(
	event_id: String,
	payload: Dictionary,
	return_scene: String = "",
	source_label: String = ""
) -> void:
	var copy := payload.duplicate()
	if not copy.has("event_id"):
		copy["event_id"] = event_id
	_apply_selection(KIND_GAME, copy, return_scene, source_label, -1, event_id)


func has_selection() -> bool:
	return _kind != "" and not _payload.is_empty()


func get_kind() -> String:
	return _kind


func get_payload() -> Dictionary:
	return _payload.duplicate()


func get_return_scene() -> String:
	return _return_scene


func get_source_label() -> String:
	return _source_label


func get_player_id() -> int:
	if _kind != KIND_PLAYER or not has_selection():
		return -1
	return _player_id


func get_event_id() -> String:
	if _kind != KIND_GAME or not has_selection():
		return ""
	return _event_id


func clear() -> void:
	_kind = ""
	_payload = {}
	_return_scene = ""
	_source_label = ""
	_player_id = -1
	_event_id = ""


func _apply_selection(
	kind: String,
	payload: Dictionary,
	return_scene: String,
	source_label: String,
	player_id: int,
	event_id: String
) -> void:
	_kind = kind
	_payload = payload.duplicate()
	_return_scene = return_scene
	_source_label = source_label
	_player_id = player_id
	_event_id = event_id
