"""
botyaraRTS - network/client.py
Сетевой клиент.
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

        # Колбэки
        self.on_command = None
        self.on_chat = None
        self.on_ping = None
        self.on_game_start = None
        self.on_pause = None
        self.on_unpause_vote = None
        self.on_disconnect = None
        self.on_upgrade_choice = None

        # Очередь входящих команд
        self.incoming_commands = []
        self.lock = threading.Lock()

    def connect(self, host, port=None):
        """Подключиться к серверу."""
        port = port or game_settings.get('server_port')
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.socket.settimeout(1.0)
            self.connected = True
            self.running = True

            self.receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self.receive_thread.start()

            print(f"[Client] Connected to {host}:{port}")
            return True

        except Exception as e:
            print(f"[Client] Connection failed: {e}")
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
        print("[Client] Disconnected")

    def send(self, pkt_type, data):
        """Отправить пакет серверу."""
        if not self.connected:
            return
        try:
            raw = encode_packet(pkt_type, data)
            self.socket.sendall(raw)
        except Exception as e:
            print(f"[Client] Send error: {e}")
            self.connected = False

    def send_command(self, command):
        """Отправить игровую команду."""
        self.send(PKT_COMMAND, command)

    def send_chat(self, text, mode='allies'):
        """Отправить сообщение в чат."""
        self.send(PKT_CHAT, make_chat_message(self.player_id, text, mode))

    def send_ping(self, world_x, world_y, ping_type='attention'):
        """Отправить пинг."""
        self.send(PKT_PING, make_ping_message(
            self.player_id, world_x, world_y, ping_type
        ))

    def send_pause(self):
        self.send(PKT_PAUSE, {'player_id': self.player_id})

    def send_unpause_vote(self):
        self.send(PKT_UNPAUSE_VOTE, {'player_id': self.player_id})

    def get_incoming_commands(self):
        """Получить и очистить входящие команды."""
        with self.lock:
            commands = list(self.incoming_commands)
            self.incoming_commands.clear()
        return commands

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
                    self._handle_packet(pkt_type, pkt_data)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Client] Receive error: {e}")
                break

        self.connected = False
        print("[Client] Connection lost")

    def _handle_packet(self, pkt_type, data):
        """Обработка входящего пакета."""
        if pkt_type == PKT_HANDSHAKE:
            self.player_id = data.get('player_id', 0)
            print(f"[Client] Assigned player_id: {self.player_id}")

        elif pkt_type == PKT_GAME_START:
            if self.on_game_start:
                self.on_game_start(data)

        elif pkt_type == PKT_COMMAND:
            with self.lock:
                self.incoming_commands.append(data)
            if self.on_command:
                self.on_command(data)

        elif pkt_type == PKT_CHAT:
            if self.on_chat:
                self.on_chat(data)

        elif pkt_type == PKT_PING:
            if self.on_ping:
                self.on_ping(data)

        elif pkt_type == PKT_PAUSE:
            if self.on_pause:
                self.on_pause(data)

        elif pkt_type == PKT_UNPAUSE_VOTE:
            if self.on_unpause_vote:
                self.on_unpause_vote(data)

        elif pkt_type == PKT_DISCONNECT:
            if self.on_disconnect:
                self.on_disconnect(data)

        elif pkt_type == PKT_UPGRADE_CHOICE:
            if self.on_upgrade_choice:
                self.on_upgrade_choice(data)