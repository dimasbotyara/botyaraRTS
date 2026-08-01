"""
botyaraRTS - core/spatial_hash.py
Пространственное хеширование для быстрого поиска объектов.
"""


class SpatialHash:
    """
    Разбивает мир на ячейки для быстрого поиска соседей.
    Вместо проверки всех N объектов, проверяем только объекты в соседних ячейках.
    """

    def __init__(self, cell_size=128):
        self.cell_size = cell_size
        self.cells = {}

    def _key(self, x, y):
        return (int(x // self.cell_size), int(y // self.cell_size))

    def clear(self):
        self.cells.clear()

    def insert(self, entity):
        """Вставить объект по его позиции."""
        key = self._key(entity.x, entity.y)
        if key not in self.cells:
            self.cells[key] = []
        self.cells[key].append(entity)

    def remove(self, entity, old_x=None, old_y=None):
        """Удалить объект из хеша."""
        x = old_x if old_x is not None else entity.x
        y = old_y if old_y is not None else entity.y
        key = self._key(x, y)
        if key in self.cells:
            try:
                self.cells[key].remove(entity)
                if not self.cells[key]:
                    del self.cells[key]
            except ValueError:
                pass

    def update_entity(self, entity, old_x, old_y):
        """Обновить позицию объекта в хеше."""
        old_key = self._key(old_x, old_y)
        new_key = self._key(entity.x, entity.y)
        if old_key != new_key:
            self.remove(entity, old_x, old_y)
            self.insert(entity)

    def query_rect(self, rect):
        """Найти все объекты в прямоугольной области."""
        results = []
        x1 = int(rect.x // self.cell_size)
        y1 = int(rect.y // self.cell_size)
        x2 = int((rect.x + rect.width) // self.cell_size)
        y2 = int((rect.y + rect.height) // self.cell_size)

        for cx in range(x1, x2 + 1):
            for cy in range(y1, y2 + 1):
                key = (cx, cy)
                if key in self.cells:
                    for entity in self.cells[key]:
                        if rect.collidepoint(entity.x, entity.y):
                            results.append(entity)
        return results

    def query_radius(self, x, y, radius):
        """Найти все объекты в радиусе от точки."""
        results = []
        r_sq = radius * radius

        cx1 = int((x - radius) // self.cell_size)
        cy1 = int((y - radius) // self.cell_size)
        cx2 = int((x + radius) // self.cell_size)
        cy2 = int((y + radius) // self.cell_size)

        for cx in range(cx1, cx2 + 1):
            for cy in range(cy1, cy2 + 1):
                key = (cx, cy)
                if key in self.cells:
                    for entity in self.cells[key]:
                        dx = entity.x - x
                        dy = entity.y - y
                        if dx * dx + dy * dy <= r_sq:
                            results.append(entity)
        return results

    def query_nearest(self, x, y, radius, filter_fn=None):
        """Найти ближайший объект в радиусе (опционально с фильтром)."""
        entities = self.query_radius(x, y, radius)
        if filter_fn:
            entities = [e for e in entities if filter_fn(e)]

        if not entities:
            return None

        nearest = None
        min_dist_sq = float('inf')
        for e in entities:
            dx = e.x - x
            dy = e.y - y
            dist_sq = dx * dx + dy * dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest = e
        return nearest

    def get_all(self):
        """Получить все объекты."""
        result = []
        for cell_entities in self.cells.values():
            result.extend(cell_entities)
        return result
