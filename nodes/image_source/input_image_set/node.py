from pathlib import Path

import cv2
import numpy as np

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


def imread_unicode(path: str, flags=cv2.IMREAD_COLOR):
    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, flags)
        return img
    except Exception as e:
        logger.error(f"Failed to read image: {path} -> {e}")
        return None


class InputImageSetNode(NodeBase):
    def execute(self) -> bool:
        source = self.params.get("source", "custom")

        if source == "previous":
            return self._execute_from_previous()

        return self._execute_custom()

    def _execute_custom(self) -> bool:
        input_images = self._get_input_images("images")
        if input_images:
            self._set_output_images("images", input_images)
            logger.info(f"[{self.meta.name}] Got {len(input_images)} images from input port")
            self.set_state(NodeState.SUCCESS)
            return True

        file_list = self.params.get("file_list", [])
        if not file_list:
            logger.warning(f"[{self.meta.name}] No input port data and no files specified")
            self.set_state(NodeState.ERROR)
            return False

        images = []
        for item in file_list:
            item_path = Path(item)
            if item_path.is_dir():
                for f in sorted(item_path.iterdir()):
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"):
                        img = imread_unicode(str(f))
                        if img is not None:
                            images.append(img)
            elif item_path.is_file():
                img = imread_unicode(str(item_path))
                if img is not None:
                    images.append(img)

        if not images:
            logger.warning(f"[{self.meta.name}] No valid images loaded from {len(file_list)} paths")
            self.set_state(NodeState.ERROR)
            return False

        self._set_output_images("images", images)
        logger.info(f"[{self.meta.name}] Loaded {len(images)} images from files")
        self.set_state(NodeState.SUCCESS)
        return True

    def _execute_from_previous(self) -> bool:
        images = self._get_input_images("images")
        if not images:
            logger.warning(f"[{self.meta.name}] No images from input port")
            self.set_state(NodeState.ERROR)
            return False

        self._set_output_images("images", images)
        logger.info(f"[{self.meta.name}] Passed through {len(images)} images")
        self.set_state(NodeState.SUCCESS)
        return True
