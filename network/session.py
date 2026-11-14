"""
botyaraRTS - network/session.py
Сетевая сессия игры: единый интерфейс для хоста и клиента.

Хост не ходит через loopback-сокет: GameServer рассылаёт пакеты
всем клиентам и дополнительно вызывает локальный hook, через который
HostSession получает те же пакеты в том же порядке (честный локстеп).

Клиент получает пакеты из потока GameClient. Оба варианта отдают
команды через общий буфер, который игра применяет на границе тика.
"""
import threading
from network.protocol import *
from network.commands import apply_command as _apply  # noqa: F401 (импорт для ясности)


class BaseSession:
    """Общий каркас: буфер входящих событий для игрового потока."""

    def __init__(self):
        self.connected = False
        self.in_game = False
        self.player_id = 0
        self._inbox = []
        self._lock = threading.Lock()
        self.status_text = ''

    # --- интерфейс, используемый игрой ---

    def send_command(self, cmd):
        raise NotImplementedError

    def queue_local_command(self, cmd):
        """Совместимое имя для issue_command."""
        self.send_command(cmd)

    def send_chat(self, text, mode='all'):
        raise NotImplementedError

    def send_ping(self, x, y, ping_type='attention'):
        raise NotImplementedError

    def send_sync_hash(self, tick, h):
        raise NotImplementedError

    def send_pause(self):
        raise NotImplementedError

    def send_unpause_vote(self):
        raise NotImplementedError

    def poll(self):
        """Забрать накопившиеся события (list of (kind, data))."""
        with self._lock:
            events = self._inbox
            self._inbox = []
        return events

    def _push(self, kind, data):
        with self._lock:
            self._inbox.append((kind, data))

    def shutdown(self):
        pass


class HostSession(BaseSession):
    """Сессия хоста: локальный доступ к GameServer."""

    def __init__(self, server):
        super().__init__()
        self.server = server
        self.connected = True
        self.player_id = server.host_id
        self.status_text = 'hosting'
        # Сервер будет дублировать рассылки в локальный буфер
        server.local_hook = self._on_broadcast

    def _alive(self):
        if not self.connected:
            return False
        with self.server.lock:
            return self.player_id in self.server.players

    def _on_broadcast(self, pkt_type, data):
        """Хук от сервера: та же последовательность пакетов, что у клиентов."""
        self._ingest(pkt_type, data)

    def _ingest(self, pkt_type, data):
        if pkt_type == PKT_COMMAND:
            self._push('cmd', data)
        elif pkt_type == PKT_CHAT:
            self._push('cmd', {'cmd': 'chat', **data})
        elif pkt_type == PKT_PING:
            self._push('cmd', {'cmd': 'ping', **data})
        elif pkt_type == PKT_SYNC_HASH:
            self._push('sync', data)
        elif pkt_type == PKT_PAUSE:
            self._push('pause', data)
        elif pkt_type == PKT_UNPAUSE_VOTE:
            self._push('unpause', data)
        elif pkt_type == PKT_DISCONNECT:
            self._push('disconnect', data)
        elif pkt_type == PKT_LOBBY_STATE:
            self._push('lobby', data)
        elif pkt_type == PKT_GAME_START:
            self._push('game_start', data)

    def send_command(self, cmd):
        # Хост обрабатывает свою команду как будто она пришла по сети
        if not self._alive():
            return
        self.server._handle_packet(self.server.players[self.player_id],
                                   PKT_COMMAND, dict(cmd))

    def send_chat(self, text, mode='all'):
        if not self._alive():
            return
        self.server._handle_packet(self.server.players[self.player_id],
                                   PKT_CHAT, {'cmd': 'chat', 'text': text,
                                              'mode': mode})

    def send_ping(self, x, y, ping_type='attention'):
        if not self._alive():
            return
        self.server._handle_packet(self.server.players[self.player_id],
                                   PKT_PING, {'cmd': 'ping', 'x': x, 'y': y,
                                              'type': ping_type})

    def send_sync_hash(self, tick, h):
        if not self._alive():
            return
        self.server._handle_packet(self.server.players[self.player_id],
                                   PKT_SYNC_HASH, {'tick': tick, 'hash': h})

    def send_pause(self):
        if not self._alive():
            return
        self.server._handle_packet(self.server.players[self.player_id],
                                   PKT_PAUSE, {'player_id': self.player_id})

    def send_unpause_vote(self):
        if not self._alive():
            return
        self.server._handle_packet(self.server.players[self.player_id],
                                   PKT_UNPAUSE_VOTE, {})

    def shutdown(self):
        self.connected = False
        self.server.local_hook = None


class RemoteSession(BaseSession):
    """Сессия подключившегося клиента."""

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.connected = client.connected
        self.player_id = client.player_id
        client.on_packet = self._on_packet
        client.on_lost = self._on_lost

    def _on_packet(self, pkt_type, data):
        if pkt_type == PKT_COMMAND:
            self._push('cmd', data)
        elif pkt_type == PKT_CHAT:
            self._push('cmd', {'cmd': 'chat', **data})
        elif pkt_type == PKT_PING:
            self._push('cmd', {'cmd': 'ping', **data})
        elif pkt_type == PKT_SYNC_HASH:
            self._push('sync', data)
        elif pkt_type == PKT_SYNC:
            self._push('tick', data)
        elif pkt_type == PKT_PAUSE:
            self._push('pause', data)
        elif pkt_type == PKT_UNPAUSE_VOTE:
            self._push('unpause', data)
        elif pkt_type == PKT_DISCONNECT:
            self._push('disconnect', data)
            self.connected = False
        elif pkt_type == PKT_LOBBY_STATE:
            self._push('lobby', data)
        elif pkt_type == PKT_JOIN_ACK:
            self.connected = True
            self.player_id = data.get('player_id', 0)
            self._push('join_ack', data)
        elif pkt_type == PKT_JOIN_REJECT:
            self._push('join_reject', data)
        elif pkt_type == PKT_GAME_START:
            self._push('game_start', data)

    def _on_lost(self):
        self.connected = False
        self._push('connection_lost', {})

    def send_command(self, cmd):
        self.client.send(PKT_COMMAND, cmd)

    def send_chat(self, text, mode='all'):
        self.client.send(PKT_CHAT, {'cmd': 'chat', 'text': text, 'mode': mode})

    def send_ping(self, x, y, ping_type='attention'):
        self.client.send(PKT_PING, {'cmd': 'ping', 'x': x, 'y': y,
                                    'type': ping_type})

    def send_sync_hash(self, tick, h):
        self.client.send(PKT_SYNC_HASH, {'tick': tick, 'hash': h})

    def send_pause(self):
        self.client.send(PKT_PAUSE, {'player_id': self.player_id})

    def send_unpause_vote(self):
        self.client.send(PKT_UNPAUSE_VOTE, {})

    def shutdown(self):
        self.client.disconnect()
