import cv2
import numpy as np

from core.image_data import ImageData, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class CircleDetectionNode(NodeBase):
    def execute(self) -> bool:
        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        dp = self.params.get("dp", 1.2)
        min_dist = self.params.get("min_dist", 50)
        param1 = self.params.get("param1", 100)
        param2 = self.params.get("param2", 30)
        min_radius = self.params.get("min_radius", 10)
        max_radius = self.params.get("max_radius", 200)

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

            result = self._detect_circles(
                img, dp, min_dist, param1, param2, min_radius, max_radius,
                color_space,
            )
            results.append(ImageData(array=result, color_space=color_space))

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] Processed {len(results)} images")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect_circles(
        self,
        img: np.ndarray,
        dp: float,
        min_dist: int,
        param1: int,
        param2: int,
        min_radius: int,
        max_radius: int,
        color_space: str = "bgr",
    ) -> np.ndarray:
        output = img.copy()
        gray = convert_to_gray(img, color_space)
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
