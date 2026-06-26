try:
    from .shapes.base import Shape
except ImportError:
    from shapes.base import Shape


class ShapeManager:
    def __init__(self):
        self._shapes: list[Shape] = []
        self._selected: Shape | None = None
        self._next_id = 0

    def add(self, shape: Shape) -> int:
        self._next_id += 1
        shape._id = self._next_id
        self._shapes.append(shape)
        return self._next_id

    def remove(self, shape: Shape) -> dict:
        state = shape.get_state_dict()
        if shape in self._shapes:
            self._shapes.remove(shape)
        if self._selected is shape:
            shape.selected = False
            self._selected = None
        return state

    def get_all(self) -> list:
        return list(self._shapes)

    def clear(self):
        self._shapes.clear()
        self._selected = None

    @property
    def selected(self) -> Shape | None:
        return self._selected

    def select(self, shape: Shape | None) -> str:
        if self._selected:
            self._selected.selected = False
        self._selected = shape
        if shape:
            shape.selected = True
            return shape.get_state_dict()
        return {}

    def delete_selected(self) -> tuple:
        if self._selected:
            state = self.remove(self._selected)
            return True, state
        return False, {}

    def get_by_id(self, shape_id: int) -> Shape | None:
        for s in self._shapes:
            if getattr(s, '_id', None) == shape_id:
                return s
        return None

    def move_to_front(self, shape: Shape):
        if shape in self._shapes:
            self._shapes.remove(shape)
            self._shapes.append(shape)

    def move_to_back(self, shape: Shape):
        if shape in self._shapes:
            self._shapes.remove(shape)
            self._shapes.insert(0, shape)

    def get_z_order(self, shape: Shape) -> int:
        try:
            return self._shapes.index(shape)
        except ValueError:
            return -1

    def get_state_summary(self) -> list:
        return [s.get_state_dict() for s in self._shapes]
