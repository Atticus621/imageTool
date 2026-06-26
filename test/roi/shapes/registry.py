class ShapeRegistry:
    _shapes: dict[str, type] = {}

    @classmethod
    def register(cls, shape_class):
        cls._shapes[shape_class.shape_type] = shape_class

    @classmethod
    def get(cls, shape_type: str) -> type | None:
        return cls._shapes.get(shape_type)

    @classmethod
    def all(cls) -> list:
        return list(cls._shapes.values())

    @classmethod
    def tool_keys(cls) -> list:
        return [s.shape_type for s in cls._shapes.values() if s.draw_mode != "none"]
