import cv2
import numpy as np

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class CircleDetectionNode(NodeBase):
    def execute(self) -> bool:
        input_images = self._get_input_images("images")
        if not input_images:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        dp = self.params.get("dp", 1.2)
        min_dist = self.params.get("min_dist", 50)
        param1 = self.params.get("param1", 100)
        param2 = self.params.get("param2", 30)
        min_radius = self.params.get("min_radius", 10)
        max_radius = self.params.get("max_radius", 200)

        results = []
        for img in input_images:
            result = self._detect_circles(
                img, dp, min_dist, param1, param2, min_radius, max_radius
            )
            results.append(result)

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] Processed {len(results)} images")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect_circles(self, img: np.ndarray, dp: float, min_dist: int,
                        param1: int, param2: int, min_radius: int,
                        max_radius: int) -> np.ndarray:
        output = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2)

        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp, min_dist,
            param1=param1, param2=param2,
            minRadius=min_radius, maxRadius=max_radius
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for c in circles[0, :]:
                center = (c[0], c[1])
                radius = c[2]
                cv2.circle(output, center, radius, (0, 255, 0), 2)
                cv2.drawMarker(output, center, (0, 0, 255),
                               cv2.MARKER_CROSS, 20, 2)

            text = f"Detected: {len(circles[0])} circles"
            color = (0, 255, 0)
        else:
            text = "Not detected"
            color = (0, 0, 255)

        cv2.putText(output, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output
