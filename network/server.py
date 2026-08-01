"""
botyaraRTS - network/server.py
Игровой сервер (TCP для надёжных данных, UDP для позиций).
"""
import socket
import threading
import json
import time
from settings import *
from network.protocol import *


class GameServer:
    """Простой игровой сервер для LAN."""

    def __init__(self, port=None):
        self.port = port or game_settings.get('server_port')
        self.running = False

        # TCP для надёжных данных (команды, чат)
        self.tcp_socket = None
        self.clients = {}  # {player_id: socket}
        self.client_threads = {}

        # Состояние
        self.game_started = False
        self.game_seed = None
        self.command_queue = []  # [(tick, command), ...]
        self.current_tick = 0
        self.tick_rate = TICK_RATE
        self.lock = threading.Lock()

        # Пауза
        self.paused = False
        self.unpause_votes = set()

    def start(self):
        """Запуск сервера."""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', self.port))
        self.tcp_socket.listen(4)
        self.tcp_socket.settimeout(1.0)
        self.running = True

        print(f"[Server] Started on port {self.port}")

        # Поток приёма подключений
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

    def stop(self):
        """Остановка сервера."""
        self.running = False
        for sock in self.clients.values():
            try:
                sock.close()
            except Exception:
                pass
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass
        print("[Server] Stopped")

    def _accept_loop(self):
        """Приём новых подключений."""
        while self.running:
            try:
                client_sock, addr = self.tcp_socket.accept()
                player_id = len(self.clients)
                self.clients[player_id] = client_sock
                print(f"[Server] Player {player_id} connected from {addr}")

                # Отправляем handshake
                self._send_to(player_id, PKT_HANDSHAKE, {
                    'player_id': player_id,
                    'port': self.port,
                })

                # Запускаем поток для этого клиента
                thread = threading.Thread(
                    target=self._client_loop,
                    args=(player_id,),
                    daemon=True
                )
                thread.start()
                self.client_threads[player_id] = thread

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Server] Accept error: {e}")

    def _client_loop(self, player_id):
        """Обработка данных от клиента."""
        sock = self.clients[player_id]
        buffer = b''

        while self.running:
            try:
                data = sock.recv(NET_BUFFER_SIZE)
                if not data:
                    break
                buffer += data

                while True:
                    pkt_type, pkt_data, buffer = decode_packet(buffer)
                    if pkt_type is None:
                        break
                    self._handle_packet(player_id, pkt_type, pkt_data)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Server] Client {player_id} error: {e}")
                break

        print(f"[Server] Player {player_id} disconnected")
        self._broadcast(PKT_DISCONNECT, {'player_id': player_id})

    def _handle_packet(self, player_id, pkt_type, data):
        """Обработка пакета от клиента."""
        if pkt_type == PKT_COMMAND:
            with self.lock:
                data['player_id'] = player_id
                data['tick'] = self.current_tick
                self.command_queue.append(data)
            # Пересылаем всем
            self._broadcast(PKT_COMMAND, data)

        elif pkt_type == PKT_CHAT:
            self._broadcast(PKT_CHAT, data)

        elif pkt_type == PKT_PING:
            self._broadcast(PKT_PING, data)

        elif pkt_type == PKT_PAUSE:
            self.paused = True
            self._broadcast(PKT_PAUSE, {'player_id': player_id})

        elif pkt_type == PKT_UNPAUSE_VOTE:
            self.unpause_votes.add(player_id)
            self._broadcast(PKT_UNPAUSE_VOTE, {
                'player_id': player_id,
                'votes': len(self.unpause_votes),
                'needed': len(self.clients),
            })
            if len(self.unpause_votes) >= len(self.clients):
                self.paused = False
                self.unpause_votes.clear()
                self._broadcast(PKT_GAME_START, {'action': 'unpause'})

        elif pkt_type == PKT_UPGRADE_CHOICE:
            # Улучшения — только для этого игрока, но синхронизируем
            self._broadcast(PKT_UPGRADE_CHOICE, data)

    def start_game(self, seed):
        """Начать игру."""
        self.game_seed = seed
        self.game_started = True
        self._broadcast(PKT_GAME_START, {
            'seed': seed,
            'players': len(self.clients),
        })

    def _send_to(self, player_id, pkt_type, data):
        """Отправить пакет одному игроку."""
        if player_id in self.clients:
            try:
                raw = encode_packet(pkt_type, data)
                self.clients[player_id].sendall(raw)
            except Exception as e:
                print(f"[Server] Send error to {player_id}: {e}")

    def _broadcast(self, pkt_type, data):
        """Отправить пакет всем игрокам."""
        raw = encode_packet(pkt_type, data)
        for pid, sock in list(self.clients.items()):
            try:
                sock.sendall(raw)
            except Exception as e:
                print(f"[Server] Broadcast error to {pid}: {e}")