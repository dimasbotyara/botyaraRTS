"""
botyaraRTS - network/server.py
LAN-сервер: фаза лобби (подключения, настройки, готовность) и
фаза игры (ретрансляция команд в порядке получения, пауза, чат).

Хост играет на этом же компьютере (локальный клиент подключается
через loopback и получает player_id 1; хост-экран — player_id 0).
"""
import socket
import threading
import time
from settings import *
from network.protocol import *


class LobbyPlayer:
    def __init__(self, player_id, name, color_index, is_ai=False, sock=None):
        self.player_id = player_id
        self.name = name
        self.color_index = color_index
        self.ready = is_ai  # ИИ всегда «готов»
        self.is_ai = is_ai
        self.sock = sock          # None для ИИ
        self.in_game = False

    def to_dict(self):
        return {
            'id': self.player_id,
            'name': self.name,
            'color': self.color_index,
            'ready': self.ready,
            'is_ai': self.is_ai,
        }


class GameServer:
    """LAN-сервер для матчей до 4 игроков."""

    def __init__(self, port=None, match_settings=None):
        self.port = port or game_settings.get('server_port')
        self.running = False
        self.phase = 'lobby'  # lobby | playing | closed

        self.tcp_socket = None
        self.lock = threading.RLock()

        # Лобби
        self.players = {}          # player_id -> LobbyPlayer
        self.match_settings = dict(match_settings or DEFAULT_MATCH_SETTINGS)
        self.host_id = 0
        self._next_player_id = 1   # 0 зарезервирован за хостом

        # Игра
        self.game_started = False
        self.game_seed = None
        self.seq = 0               # глобальный порядок команд
        self._game_start_walltime = None
        self._loaded_players = set()
        self._sync_thread = None

        # Локальный хук: дублировать рассылки хосту (он без сокета)
        self.local_hook = None

        # Пауза
        self.paused = False
        self.unpause_votes = set()

    # ========================================
    # ЖИЗНЕННЫЙ ЦИКЛ
    # ========================================

    def start(self):
        """Запуск сервера."""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', self.port))
        self.tcp_socket.listen(4)
        self.tcp_socket.settimeout(0.5)
        self.running = True

        # Хост — локальный игрок (id 0)
        host_name = game_settings.get('player_name') or 'Host'
        self.players[0] = LobbyPlayer(0, host_name,
                                      game_settings.get('player_color'),
                                      is_ai=False, sock=None)

        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()
        return True

    def stop(self):
        """Остановка сервера."""
        self.running = False
        self.phase = 'closed'
        with self.lock:
            for p in self.players.values():
                if p.sock:
                    try:
                        p.sock.close()
                    except Exception:
                        pass
            self.players.clear()
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass

    # ========================================
    # ЛОББИ
    # ========================================

    def _accept_loop(self):
        """Приём подключений (только в фазе лобби)."""
        while self.running:
            try:
                client_sock, addr = self.tcp_socket.accept()
                client_sock.settimeout(1.0)
                with self.lock:
                    if self.phase != 'lobby' or len(self.players) >= 4:
                        try:
                            client_sock.sendall(encode_packet(PKT_JOIN_REJECT,
                                                              {'reason': 'full_or_started'}))
                        except Exception:
                            pass
                        client_sock.close()
                        continue
                thread = threading.Thread(target=self._client_loop,
                                          args=(client_sock,), daemon=True)
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    time.sleep(0.1)

    def _client_loop(self, sock):
        """Обработка подключившегося клиента до JOIN_REQ и после."""
        player = None
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
                    if player is None:
                        player = self._handle_join(sock, pkt_type, pkt_data)
                        if player is None and pkt_type == PKT_JOIN_REQ:
                            return  # отказ — закрываем
                    else:
                        self._handle_packet(player, pkt_type, pkt_data)
            except socket.timeout:
                continue
            except Exception as e:
                import traceback
                print(f"[Server] client {player.player_id if player else '?'} "
                      f"loop error: {e}")
                traceback.print_exc()
                break

        # Дисконнект
        if player is not None:
            self._on_player_left(player)

    def _handle_join(self, sock, pkt_type, data):
        """Первый пакет от клиента — запрос на вход в лобби."""
        if pkt_type != PKT_JOIN_REQ:
            return None
        with self.lock:
            if self.phase != 'lobby' or len(self.players) >= 4:
                try:
                    sock.sendall(encode_packet(PKT_JOIN_REJECT,
                                               {'reason': 'full_or_started'}))
                except Exception:
                    pass
                return None

            player_id = self._next_player_id
            self._next_player_id += 1
            name = str(data.get('name', f'Player {player_id + 1}'))[:20]
            color = int(data.get('color_index', player_id)) % len(PLAYER_COLORS)
            # Цвет не должен совпадать с уже занятыми
            used = {p.color_index for p in self.players.values()}
            if color in used:
                for c in range(len(PLAYER_COLORS)):
                    if c not in used:
                        color = c
                        break

            player = LobbyPlayer(player_id, name, color, is_ai=False, sock=sock)
            self.players[player_id] = player

            lobby = self._lobby_dict()
            try:
                sock.sendall(encode_packet(PKT_JOIN_ACK,
                                           {'player_id': player_id, 'lobby': lobby}))
            except Exception:
                del self.players[player_id]
                return None

            self._broadcast_lobby()
            return player

    def add_ai_slot(self):
        """Добавить ИИ-слот (только хост)."""
        with self.lock:
            if self.phase != 'lobby' or len(self.players) >= 4:
                return False
            player_id = self._next_player_id
            self._next_player_id += 1
            used = {p.color_index for p in self.players.values()}
            color = next((c for c in range(len(PLAYER_COLORS)) if c not in used), 0)
            self.players[player_id] = LobbyPlayer(player_id, f"AI {player_id}",
                                                  color, is_ai=True, sock=None)
            self._broadcast_lobby()
            return True

    def remove_player(self, player_id):
        """Удалить игрока/ИИ-слот (хост)."""
        with self.lock:
            p = self.players.get(player_id)
            if not p or player_id == self.host_id:
                return False
            if p.sock:
                try:
                    p.sock.close()
                except Exception:
                    pass
            del self.players[player_id]
            self._broadcast_lobby()
            return True

    def set_settings(self, settings):
        """Обновить настройки матча (только хост)."""
        with self.lock:
            if self.phase != 'lobby':
                return
            for key in ('map_size', 'start_resources', 'resource_density',
                        'ai_difficulty', 'ai_strategy'):
                if key in settings:
                    self.match_settings[key] = settings[key]
            self._broadcast_lobby()

    def _lobby_dict(self):
        return {
            'players': [p.to_dict() for p in self.players.values()],
            'settings': dict(self.match_settings),
            'host_id': self.host_id,
            'phase': self.phase,
        }

    def _broadcast_lobby(self):
        self._broadcast(PKT_LOBBY_STATE, self._lobby_dict())

    def try_start_game(self, requester_id):
        """Хост жмёт «старт»: все люди должны быть готовыми."""
        with self.lock:
            if self.phase != 'lobby' or requester_id != self.host_id:
                return False
            humans = [p for p in self.players.values() if not p.is_ai]
            # Хост готов по определению — он и жмёт «старт»
            if not all(p.ready or p.player_id == self.host_id for p in humans) \
                    or len(self.players) < 2:
                return False

            seed = int(time.time() * 1000) % 1000000
            self.game_seed = seed
            self.phase = 'playing'
            self.game_started = True

            self._broadcast(PKT_GAME_START, {
                'seed': seed,
                'settings': dict(self.match_settings),
                'players': [p.to_dict() for p in self.players.values()],
            })
            return True

    def _current_tick(self):
        """Текущий тик сервера от момента «begin»."""
        if self._game_start_walltime is None:
            return 0
        return int((time.time() - self._game_start_walltime) * SIM_RATE)

    def _notify_loaded(self, player_id):
        """Клиент доложил о готовности симуляции — ждём всех и запускаем."""
        with self.lock:
            self._loaded_players.add(player_id)
            # Хост тоже участвует в handshake (его сокета просто нет)
            humans = [p for p in self.players.values() if not p.is_ai]
        if all(p.player_id in self._loaded_players for p in humans):
            with self.lock:
                if self._game_start_walltime is not None:
                    return
                self._game_start_walltime = time.time()
                self._loaded_players.clear()
            self._broadcast(PKT_GAME_START, {'action': 'begin'})
            self._sync_thread = threading.Thread(
                target=self._sync_loop, daemon=True)
            self._sync_thread.start()

    def _sync_loop(self):
        """Регулярная рассылка тика сервера для темпа клиентов."""
        while self.running and self.phase == 'playing':
            self._broadcast(PKT_SYNC, {'tick': self._current_tick()})
            time.sleep(0.2)

    def _on_player_left(self, player):
        with self.lock:
            if self.players.get(player.player_id) is player:
                del self.players[player.player_id]
            if self.phase == 'playing':
                self._broadcast(PKT_DISCONNECT,
                                {'player_id': player.player_id,
                                 'name': player.name})
                self.phase = 'closed'
            else:
                self._broadcast_lobby()

    # ========================================
    # ФАЗА ИГРЫ
    # ========================================

    def _handle_packet(self, player, pkt_type, data):
        """Пакеты от идентифицированного клиента."""
        if pkt_type == PKT_LOBBY_SET:
            self._handle_lobby_set(player, data)

        elif pkt_type == PKT_COMMAND:
            # Штампуем seq и ЦЕЛЕВОЙ ТИК (локстеп) и рассылаем всем
            with self.lock:
                data['player_id'] = player.player_id
                data['seq'] = self.seq
                data['tick'] = self._current_tick() + LOCKSTEP_DELAY
                self.seq += 1
            self._broadcast(PKT_COMMAND, data)

        elif pkt_type == PKT_CHAT:
            data['player_id'] = player.player_id
            # Отправителю не ретранслируем: он уже показал сообщение локально
            self._broadcast(PKT_CHAT, data, exclude=player.player_id)

        elif pkt_type == PKT_PING:
            data['player_id'] = player.player_id
            self._broadcast(PKT_PING, data, exclude=player.player_id)

        elif pkt_type == PKT_PAUSE:
            self._broadcast(PKT_PAUSE, {'player_id': player.player_id})

        elif pkt_type == PKT_UNPAUSE_VOTE:
            self.unpause_votes.add(player.player_id)
            humans = [p for p in self.players.values() if not p.is_ai]
            votes, needed = len(self.unpause_votes), len(humans)
            self._broadcast(PKT_UNPAUSE_VOTE, {
                'player_id': player.player_id,
                'votes': votes, 'needed': needed,
            })
            if votes >= needed:
                self.paused = False
                self.unpause_votes.clear()
                self._broadcast(PKT_GAME_START, {'action': 'unpause'})

        elif pkt_type == PKT_SYNC_HASH:
            data['player_id'] = player.player_id
            self._broadcast(PKT_SYNC_HASH, data, exclude=player.player_id)


    def _handle_lobby_set(self, player, data):
        if data.get('loaded'):
            self._notify_loaded(player.player_id)
            return
        with self.lock:
            if data.get('leave'):
                player.ready = False
                # клиент сам закроет соединение
                return
            if 'ready' in data:
                player.ready = bool(data['ready'])
            if player.player_id == self.host_id:
                if 'settings' in data and isinstance(data['settings'], dict):
                    for key in ('map_size', 'start_resources', 'resource_density',
                                'ai_difficulty', 'ai_strategy'):
                        if key in data['settings']:
                            self.match_settings[key] = data['settings'][key]
                if data.get('add_ai'):
                    if self.phase == 'lobby' and len(self.players) < 4:
                        player_id = self._next_player_id
                        self._next_player_id += 1
                        used = {p.color_index for p in self.players.values()}
                        color = next((c for c in range(len(PLAYER_COLORS))
                                      if c not in used), 0)
                        self.players[player_id] = LobbyPlayer(
                            player_id, f"AI {player_id}", color,
                            is_ai=True, sock=None)
                if 'remove_player' in data:
                    rid = int(data['remove_player'])
                    p = self.players.get(rid)
                    if p and rid != self.host_id:
                        if p.sock:
                            try:
                                p.sock.close()
                            except Exception:
                                pass
                        del self.players[rid]
                if data.get('start'):
                    # рекурсивно через try_start_game вне lock
                    pass
            self._broadcast_lobby()
        if data.get('start'):
            self.try_start_game(player.player_id)

    # ========================================
    # ОТПРАВКА
    # ========================================

    def _send_to(self, player, pkt_type, data):
        sock = player.sock
        if sock is None:
            return
        try:
            sock.sendall(encode_packet(pkt_type, data))
        except Exception:
            pass

    def _broadcast(self, pkt_type, data, exclude=None):
        if exclude is None and self.local_hook:
            try:
                self.local_hook(pkt_type, data)
            except Exception:
                pass
        raw = encode_packet(pkt_type, data)
        with self.lock:
            players = list(self.players.values())
        for p in players:
            if exclude is not None and p.player_id == exclude:
                continue
            if p.sock is None:
                continue
            try:
                p.sock.sendall(raw)
            except Exception:
                pass
