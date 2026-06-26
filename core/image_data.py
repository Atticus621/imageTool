"""ImageData — value object encapsulating a numpy image array.

UI code depends on this instead of raw np.ndarray so that image
metadata (width, height, channels) is available without numpy imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class ImageData:
    """Immutable wrapper around a numpy image array.

    Provides width/height/channels without callers needing numpy.
    The underlying array is shared (not copied) for zero overhead.
    """

    array: np.ndarray = field(repr=False)

    @property
    def width(self) -> int:
        return self.array.shape[1]

    @property
    def height(self) -> int:
        return self.array.shape[0]

    @property
    def channels(self) -> int:
        s = self.array.shape
        return s[2] if len(s) >= 3 else 1

    @property
    def is_grayscale(self) -> bool:
        return self.channels == 1

    @property
    def shape(self) -> tuple[int, ...]:
        return self.array.shape
