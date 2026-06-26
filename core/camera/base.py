from abc import ABC, abstractmethod
import numpy as np


class ICamera(ABC):
    @abstractmethod
    def connect(self, device_id: int = 0) -> bool:
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def grab_frame(self) -> "np.ndarray | None":
        pass
