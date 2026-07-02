import cv2
import numpy as np

from core.image_data import ImageData, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class PolygonDetectionNode(NodeBase):
    def execute(self) -> bool:
        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        epsilon_factor = self.params.get("epsilon_factor", 0.02)
        min_area = self.params.get("min_area", 500)

        results: list[ImageData] = []
        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            elif isinstance(item, np.ndarray):
                img = item
                color_space = "bgr"
            else:
                continue

            result = self._detect_polygons(img, epsilon_factor, min_area, color_space)
            results.append(ImageData(array=result, color_space=color_space))

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] Processed {len(results)} images")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect_polygons(
        self,
        img: np.ndarray,
        epsilon_factor: float,
        min_area: int,
        color_space: str = "bgr",
    ) -> np.ndarray:
        output = img.copy()
        gray = convert_to_gray(img, color_space)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) >= 3:
                cv2.drawContours(output, [approx], 0, (0, 255, 0), 2)
                count += 1

        if count > 0:
            text = f"Detected: {count} polygons"
            color = (0, 255, 0)
        else:
            text = "Not detected"
            color = (0, 0, 255)

        cv2.putText(output, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output
