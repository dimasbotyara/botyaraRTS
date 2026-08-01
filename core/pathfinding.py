"""
botyaraRTS - core/pathfinding.py
A* поиск пути по тайловой сетке.
Поддержка разных высот, рамп и стен.
"""
import heapq
import math
from settings import *


class PathNode:
    __slots__ = ['x', 'y', 'g', 'h', 'f', 'parent']

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.g = 0
        self.h = 0
        self.f = 0
        self.parent = None

    def __lt__(self, other):
        return self.f < other.f


def heuristic(x1, y1, x2, y2):
    """Октильное расстояние (допускает диагональ)."""
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    return max(dx, dy) + 0.414 * min(dx, dy)


def find_path(tilemap, start_tx, start_ty, end_tx, end_ty, max_iterations=5000):
    """
    A* поиск пути от (start_tx, start_ty) до (end_tx, end_ty) по тайлам.

    tilemap: объект TileMap с методами is_walkable() и get_height()
    Возвращает список тайловых координат [(tx, ty), ...] или None если путь не найден.
    """
    # Проверки
    if not tilemap.is_walkable(start_tx, start_ty):
        return None
    if not tilemap.is_walkable(end_tx, end_ty):
        # Ищем ближайший проходимый тайл к цели
        end_tx, end_ty = _find_nearest_walkable(tilemap, end_tx, end_ty)
        if end_tx is None:
            return None

    if start_tx == end_tx and start_ty == end_ty:
        return [(end_tx, end_ty)]

    # A*
    open_heap = []
    start_node = PathNode(start_tx, start_ty)
    start_node.h = heuristic(start_tx, start_ty, end_tx, end_ty)
    start_node.f = start_node.h
    heapq.heappush(open_heap, start_node)

    closed_set = set()
    open_dict = {(start_tx, start_ty): start_node}

    iterations = 0

    # 8 направлений движения
    neighbors = [
        (-1, -1), (0, -1), (1, -1),
        (-1, 0),           (1, 0),
        (-1, 1),  (0, 1),  (1, 1)
    ]

    while open_heap and iterations < max_iterations:
        iterations += 1
        current = heapq.heappop(open_heap)
        cx, cy = current.x, current.y

        if cx == end_tx and cy == end_ty:
            # Восстановить путь
            path = []
            node = current
            while node:
                path.append((node.x, node.y))
                node = node.parent
            path.reverse()
            return path

        closed_set.add((cx, cy))
        if (cx, cy) in open_dict:
            del open_dict[(cx, cy)]

        current_height = tilemap.get_height(cx, cy)

        for dx, dy in neighbors:
            nx, ny = cx + dx, cy + dy

            if (nx, ny) in closed_set:
                continue
            if not tilemap.is_walkable(nx, ny):
                continue

            neighbor_height = tilemap.get_height(nx, ny)

            # Проверка перехода высот
            # Можно перейти только через рампу или на тот же уровень
            if abs(neighbor_height - current_height) > 0:
                if not tilemap.is_ramp(nx, ny) and not tilemap.is_ramp(cx, cy):
                    continue

            # Диагональ: проверяем что не срезаем угол через стену
            if dx != 0 and dy != 0:
                if not tilemap.is_walkable(cx + dx, cy) or \
                   not tilemap.is_walkable(cx, cy + dy):
                    continue

            # Стоимость перемещения
            move_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
            # Подъем дороже
            if neighbor_height > current_height:
                move_cost *= 1.5

            new_g = current.g + move_cost

            existing = open_dict.get((nx, ny))
            if existing and new_g >= existing.g:
                continue

            node = PathNode(nx, ny)
            node.g = new_g
            node.h = heuristic(nx, ny, end_tx, end_ty)
            node.f = node.g + node.h
            node.parent = current

            open_dict[(nx, ny)] = node
            heapq.heappush(open_heap, node)

    return None  # Путь не найден


def _find_nearest_walkable(tilemap, tx, ty, max_radius=10):
    """Найти ближайший проходимый тайл к данному."""
    for r in range(1, max_radius + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if abs(dx) == r or abs(dy) == r:
                    nx, ny = tx + dx, ty + dy
                    if tilemap.is_walkable(nx, ny):
                        return nx, ny
    return None, None


def smooth_path(path, tilemap):
    """
    Сглаживание пути — убирает лишние промежуточные точки,
    оставляя только повороты.
    """
    if not path or len(path) <= 2:
        return path

    smoothed = [path[0]]
    for i in range(1, len(path) - 1):
        prev = path[i - 1]
        curr = path[i]
        next_p = path[i + 1]

        # Если направление изменилось — оставляем точку
        dx1 = curr[0] - prev[0]
        dy1 = curr[1] - prev[1]
        dx2 = next_p[0] - curr[0]
        dy2 = next_p[1] - curr[1]

        if dx1 != dx2 or dy1 != dy2:
            smoothed.append(curr)

    smoothed.append(path[-1])
    return smoothed


def path_exists(tilemap, start_tx, start_ty, end_tx, end_ty):
    """Быстрая проверка существования пути (BFS с лимитом)."""
    if not tilemap.is_walkable(start_tx, start_ty) or \
       not tilemap.is_walkable(end_tx, end_ty):
        return False

    from collections import deque
    visited = set()
    queue = deque([(start_tx, start_ty)])
    visited.add((start_tx, start_ty))
    max_iter = 10000

    while queue and max_iter > 0:
        max_iter -= 1
        x, y = queue.popleft()
        if x == end_tx and y == end_ty:
            return True

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited and tilemap.is_walkable(nx, ny):
                h1 = tilemap.get_height(x, y)
                h2 = tilemap.get_height(nx, ny)
                if abs(h2 - h1) <= 0 or tilemap.is_ramp(nx, ny) or tilemap.is_ramp(x, y):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return False
