"""
botyaraRTS - network/protocol.py
Сетевой протокол: сериализация пакетов и игровых команд.

Формат пакета: [2 байта длины][1 байт типа][JSON данные]
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

# Лобби (v2)
PKT_JOIN_REQ = 0x0B      # клиент → сервер: {name, color_index, version}
PKT_JOIN_ACK = 0x0C      # сервер → клиент: {player_id, lobby}
PKT_JOIN_REJECT = 0x0D   # сервер → клиент: {reason}
PKT_LOBBY_STATE = 0x0E   # сервер → всем: {players, settings, host_id, phase}
PKT_LOBBY_SET = 0x0F     # клиент → сервер: {ready?/settings?/start?/leave?}
PKT_SYNC_HASH = 0x10     # оба направления: {player_id, tick, hash}


MAX_PACKET_SIZE = 64 * 1024


def encode_packet(packet_type, data):
    """Кодировать пакет: [2 байта длины][1 байт типа][JSON данные]"""
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    length = len(json_data) + 1  # +1 для типа
    header = struct.pack('!HB', length, packet_type)
    return header + json_data


def decode_packet(raw_bytes):
    """Декодировать пакет. Возвращает (тип, данные, остаток).

    Битые JSON-полезные нагрузки отбрасываются (возвращается пустой dict),
    чтобы один повреждённый пакет не ронял соединение.
    """
    if len(raw_bytes) < 3:
        return None, None, raw_bytes

    length, packet_type = struct.unpack('!HB', raw_bytes[:3])

    if length > MAX_PACKET_SIZE:
        # Повреждённый заголовок — сбрасываем буфер
        return None, None, b''

    if len(raw_bytes) < 3 + length - 1:
        return None, None, raw_bytes  # Неполный пакет

    json_data = raw_bytes[3:3 + length - 1]
    remainder = raw_bytes[3 + length - 1:]

    try:
        data = json.loads(json_data.decode('utf-8'))
        if not isinstance(data, dict):
            data = {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}

    return packet_type, data, remainder


# ========================================
# Игровые команды (сетевые и локальные)
# ========================================
# Все команды — плоские JSON-словари; ссылки на объекты передаются по id.

def make_move_command(player_id, unit_ids, x, y, attack_move=False):
    return {'cmd': 'move', 'player_id': player_id, 'unit_ids': unit_ids,
            'x': x, 'y': y, 'attack_move': bool(attack_move)}


def make_attack_command(player_id, unit_ids, target_id):
    return {'cmd': 'attack', 'player_id': player_id, 'unit_ids': unit_ids,
            'target_id': target_id}


def make_build_command(player_id, building_name, tile_x, tile_y):
    return {'cmd': 'build', 'player_id': player_id,
            'building': building_name, 'tx': tile_x, 'ty': tile_y}


def make_produce_command(player_id, building_id, unit_name):
    return {'cmd': 'produce', 'player_id': player_id,
            'building_id': building_id, 'unit': unit_name}


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
