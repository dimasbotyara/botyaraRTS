"""
botyaraRTS - network/protocol.py
Сетевой протокол: сериализация команд.
"""
import json
import struct


# Типы пакетов
PKT_HANDSHAKE = 0x01
PKT_GAME_START = 0x02
PKT_COMMAND = 0x03
PKT_SYNC = 0x04
PKT_CHAT = 0x05
PKT_PING = 0x06
PKT_PAUSE = 0x07
PKT_UNPAUSE_VOTE = 0x08
PKT_DISCONNECT = 0x09
PKT_UPGRADE_CHOICE = 0x0A


def encode_packet(packet_type, data):
    """Кодировать пакет: [2 байта длины][1 байт типа][JSON данные]"""
    json_data = json.dumps(data).encode('utf-8')
    length = len(json_data) + 1  # +1 для типа
    header = struct.pack('!HB', length, packet_type)
    return header + json_data


def decode_packet(raw_bytes):
    """Декодировать пакет. Возвращает (тип, данные, остаток)."""
    if len(raw_bytes) < 3:
        return None, None, raw_bytes

    length, packet_type = struct.unpack('!HB', raw_bytes[:3])

    if len(raw_bytes) < 3 + length - 1:
        return None, None, raw_bytes  # Неполный пакет

    json_data = raw_bytes[3:3 + length - 1]
    remainder = raw_bytes[3 + length - 1:]

    try:
        data = json.loads(json_data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}

    return packet_type, data, remainder


# Команды для lockstep
def make_move_command(player_id, unit_ids, target_x, target_y):
    return {
        'cmd': 'move',
        'player_id': player_id,
        'unit_ids': unit_ids,
        'target_x': target_x,
        'target_y': target_y,
    }


def make_attack_command(player_id, unit_ids, target_id):
    return {
        'cmd': 'attack',
        'player_id': player_id,
        'unit_ids': unit_ids,
        'target_id': target_id,
    }


def make_build_command(player_id, building_type, tile_x, tile_y):
    return {
        'cmd': 'build',
        'player_id': player_id,
        'building_type': building_type,
        'tile_x': tile_x,
        'tile_y': tile_y,
    }


def make_produce_command(player_id, building_id, unit_type):
    return {
        'cmd': 'produce',
        'player_id': player_id,
        'building_id': building_id,
        'unit_type': unit_type,
    }


def make_chat_message(player_id, text, mode='allies'):
    return {
        'cmd': 'chat',
        'player_id': player_id,
        'text': text,
        'mode': mode,
    }


def make_ping_message(player_id, world_x, world_y, ping_type='attention'):
    return {
        'cmd': 'ping',
        'player_id': player_id,
        'x': world_x,
        'y': world_y,
        'type': ping_type,
    }