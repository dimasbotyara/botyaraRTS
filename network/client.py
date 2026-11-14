"""
botyaraRTS - network/client.py
Сетевой клиент: подключение к LAN-серверу, поток приёма пакетов.

Все входящие пакеты передаются наверх через колбэк on_packet;
обрыв соединения — через on_lost. Разбор лобби/игры — в session.py.
"""
import socket
import threading
from settings import *
from network.protocol import *


class GameClient:
    """Клиент для подключения к серверу."""

    def __init__(self):
        self.socket = None
        self.connected = False
        self.player_id = -1
        self.receive_thread = None
        self.running = False
        self.buffer = b''

        # Колбэки (назначаются сессией)
        self.on_packet = None   # fn(pkt_type, data)
        self.on_lost = None     # fn()

    def connect(self, host, port=None, name=None, color_index=0, timeout=3.0):
        """Подключиться и запросить вход в лобби."""
        port = port or game_settings.get('server_port')
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((host, port))
            self.socket.settimeout(1.0)
            self.connected = True
            self.running = True

            self.receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self.receive_thread.start()

            # Запрос на вход в лобби
            self.send(PKT_JOIN_REQ, {
                'name': name or game_settings.get('player_name') or 'Player',
                'color_index': color_index,
                'version': NET_PROTOCOL_VERSION,
            })
            return True

        except Exception:
            self.connected = False
            return False

    def disconnect(self):
        """Отключиться."""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.send(PKT_DISCONNECT, {'player_id': self.player_id})
                self.socket.close()
            except Exception:
                pass

    def send(self, pkt_type, data):
        """Отправить пакет серверу."""
        if not self.connected:
            return
        try:
            raw = encode_packet(pkt_type, data)
            self.socket.sendall(raw)
        except Exception:
            self.connected = False

    def _receive_loop(self):
        """Поток приёма данных."""
        while self.running:
            try:
                data = self.socket.recv(NET_BUFFER_SIZE)
                if not data:
                    break
                self.buffer += data

                while True:
                    pkt_type, pkt_data, self.buffer = decode_packet(self.buffer)
                    if pkt_type is None:
                        break
                    if self.on_packet:
                        try:
                            self.on_packet(pkt_type, pkt_data)
                        except Exception:
                            pass

            except socket.timeout:
                continue
            except Exception:
                break

        self.connected = False
        if self.on_lost:
            try:
                self.on_lost()
            except Exception:
                pass
