import cv2
import numpy as np

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class PolygonDetectionNode(NodeBase):
    def execute(self) -> bool:
        input_images = self._get_input_images("images")
        if not input_images:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        results = []
        for img in input_images:
            result = self._detect_polygons(img)
            results.append(result)

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] Processed {len(results)} images")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect_polygons(self, img: np.ndarray) -> np.ndarray:
        output = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        epsilon_factor = self.params.get("epsilon_factor", 0.02)
        min_area = self.params.get("min_area", 500)

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
