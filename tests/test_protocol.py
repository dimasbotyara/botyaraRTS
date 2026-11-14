"""
botyaraRTS - tests/test_protocol.py
Кодек пакетов и фабрики команд.
"""
from network.protocol import (
    encode_packet, decode_packet,
    PKT_COMMAND, PKT_CHAT, PKT_JOIN_REQ, PKT_LOBBY_STATE, PKT_GAME_START,
    PKT_SYNC, PKT_SYNC_HASH,
    make_move_command, make_chat_message,
)


def test_encode_decode_roundtrip():
    data = {'cmd': 'move', 'unit_ids': [1, 2, 3], 'x': 10.5, 'y': -3.25}
    raw = encode_packet(PKT_COMMAND, data)
    pkt_type, parsed, remainder = decode_packet(raw)
    assert pkt_type == PKT_COMMAND
    assert parsed == data
    assert remainder == b''


def test_decode_cyrillic():
    raw = encode_packet(PKT_CHAT, make_chat_message(1, 'привет ⚔'))
    pkt_type, parsed, _ = decode_packet(raw)
    assert pkt_type == PKT_CHAT
    assert parsed['text'] == 'привет ⚔'


def test_decode_partial_buffer():
    raw = encode_packet(PKT_SYNC, {'tick': 42})
    pkt_type, parsed, remainder = decode_packet(raw[:5])
    assert pkt_type is None          # неполный пакет
    assert remainder == raw[:5]      # данные сохранены


def test_decode_corrupt_json_is_safe():
    raw = encode_packet(PKT_SYNC, {'tick': 1})
    corrupted = raw[:3] + b'{broken json!!!'
    pkt_type, parsed, remainder = decode_packet(corrupted)
    # Не должно падать; битая полезная нагрузка -> пустой dict
    assert pkt_type == PKT_SYNC
    assert parsed == {}


def test_decode_garbage_header_is_safe():
    # Заведомо неполный пакет с огромной заявленной длиной просто ждёт хвоста
    pkt_type, parsed, remainder = decode_packet(b'\xff\xff\xff' + b'garbage' * 100)
    assert pkt_type is None
    assert remainder == b'\xff\xff\xff' + b'garbage' * 100


def test_lobby_packets_roundtrip():
    lobby = {'players': [{'id': 0, 'name': 'Игрок', 'ready': True}],
             'settings': {'map_size': 'medium'}, 'host_id': 0}
    raw = encode_packet(PKT_LOBBY_STATE, lobby)
    pkt_type, parsed, _ = decode_packet(raw)
    assert pkt_type == PKT_LOBBY_STATE
    assert parsed['players'][0]['name'] == 'Игрок'


def test_command_factories():
    cmd = make_move_command(0, [5, 6], 100.0, 200.0, attack_move=True)
    assert cmd['cmd'] == 'move'
    assert cmd['attack_move'] is True
    raw = encode_packet(PKT_COMMAND, cmd)
    _, parsed, _ = decode_packet(raw)
    assert parsed == cmd
