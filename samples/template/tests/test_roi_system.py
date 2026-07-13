"""ROI 系统单元测试。

覆盖：
- ROIData 数据类
- 各转换器（circle, polygon, rectangle, mask）
- ROIManager 创建、合并、约束
- ROITracer 追踪
- ROISerializer 序列化
- 端口类型校验
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试前重置单例。"""
    from core.roi.manager import ROIManager
    from core.roi.tracer import ROITracer
    ROIManager.reset()
    ROITracer.reset()
    yield
    ROIManager.reset()
    ROITracer.reset()


@pytest.fixture
def roi_mgr():
    from core.roi.manager import ROIManager
    return ROIManager.instance()


@pytest.fixture
def tracer():
    from core.roi.tracer import ROITracer
    return ROITracer.instance()


# ── ROIData ──────────────────────────────────────────────────────────

class TestROIData:
    def test_create_with_auto_trace_id(self):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="circle", data=(100, 200, 50))
        assert roi.roi_type == "circle"
        assert roi.data == (100, 200, 50)
        assert roi.trace_id.startswith("roi_")
        assert len(roi.trace_id) == 12  # "roi_" + 8 hex chars

    def test_create_with_custom_trace_id(self):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="circle", data=(100, 200, 50), trace_id="custom_id")
        assert roi.trace_id == "custom_id"

    def test_frozen(self):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="circle", data=(100, 200, 50))
        with pytest.raises(AttributeError):
            roi.roi_type = "polygon"

    def test_repr(self):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="circle", data=(100, 200, 50), image_size=(1920, 1080))
        r = repr(roi)
        assert "circle" in r
        assert "(1920, 1080)" in r


class TestROIError:
    def test_with_trace_id(self):
        from core.roi.data import ROIError
        err = ROIError("test error", trace_id="roi_abc12345")
        assert "roi_abc12345" in str(err)
        assert err.trace_id == "roi_abc12345"

    def test_with_cause(self):
        from core.roi.data import ROIError
        cause = ValueError("original")
        err = ROIError("wrapped", cause=cause)
        assert err.cause is cause


# ── Converters ───────────────────────────────────────────────────────

class TestCircleConverter:
    def test_to_mask(self, roi_mgr):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="circle", data=(100, 100, 50), image_size=(200, 200))
        mask = roi_mgr.to_mask(roi, (200, 200))
        assert mask.dtype == bool
        assert mask.shape == (200, 200)
        assert mask[100, 100]  # center should be in mask
        assert not mask[0, 0]  # corner should be outside

    def test_bbox(self, roi_mgr):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="circle", data=(100, 200, 50))
        bbox = roi_mgr.bbox(roi)
        assert bbox == (50, 150, 100, 100)

    def test_validate_negative_radius(self, roi_mgr):
        from core.roi.converter import converter_registry
        from core.roi.data import ROIData
        conv = converter_registry.get("circle")
        roi = ROIData(roi_type="circle", data=(100, 100, -5))
        warnings = conv.validate(roi)
        assert len(warnings) > 0


class TestPolygonConverter:
    def test_to_mask(self, roi_mgr):
        from core.roi.data import ROIData
        # Simple triangle
        vertices = [[10, 10], [100, 10], [50, 100]]
        roi = ROIData(roi_type="polygon", data=vertices, image_size=(200, 200))
        mask = roi_mgr.to_mask(roi, (200, 200))
        assert mask.dtype == bool
        assert mask.shape == (200, 200)
        assert mask[50, 50]  # inside triangle

    def test_validate_too_few_vertices(self):
        from core.roi.converter import converter_registry
        from core.roi.data import ROIData
        conv = converter_registry.get("polygon")
        roi = ROIData(roi_type="polygon", data=[[0, 0], [1, 1]])
        warnings = conv.validate(roi)
        assert any("vertices" in w.lower() for w in warnings)


class TestRectangleConverter:
    def test_to_mask(self, roi_mgr):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="rectangle", data=(10, 20, 100, 50), image_size=(200, 200))
        mask = roi_mgr.to_mask(roi, (200, 200))
        assert mask[20, 10]  # top-left corner
        assert mask[69, 109]  # bottom-right corner
        assert not mask[0, 0]  # outside

    def test_bbox(self, roi_mgr):
        from core.roi.data import ROIData
        roi = ROIData(roi_type="rectangle", data=(10, 20, 100, 50))
        bbox = roi_mgr.bbox(roi)
        assert bbox == (10, 20, 100, 50)


class TestMaskConverter:
    def test_to_mask_same_size(self, roi_mgr):
        from core.roi.data import ROIData
        mask_data = np.zeros((100, 200), dtype=np.uint8)
        mask_data[20:80, 50:150] = 1
        roi = ROIData(roi_type="mask", data=mask_data, image_size=(200, 100))
        mask = roi_mgr.to_mask(roi, (200, 100))
        assert mask.dtype == bool
        assert mask[50, 100]
        assert not mask[0, 0]

    def test_to_mask_resize(self, roi_mgr):
        from core.roi.data import ROIData
        mask_data = np.zeros((50, 100), dtype=np.uint8)
        mask_data[10:40, 20:80] = 1
        roi = ROIData(roi_type="mask", data=mask_data, image_size=(100, 50))
        mask = roi_mgr.to_mask(roi, (200, 100))
        assert mask.shape == (100, 200)


# ── ConverterRegistry ────────────────────────────────────────────────

class TestConverterRegistry:
    def test_unknown_type_raises(self):
        from core.roi.converter import converter_registry
        with pytest.raises(KeyError, match="Unknown ROI type"):
            converter_registry.get("nonexistent")

    def test_has_registered_types(self):
        from core.roi.converter import converter_registry
        assert converter_registry.has("circle")
        assert converter_registry.has("polygon")
        assert converter_registry.has("rectangle")
        assert converter_registry.has("mask")

    def test_all_types(self):
        from core.roi.converter import converter_registry
        types = converter_registry.all_types()
        assert "circle" in types
        assert "polygon" in types
        assert "rectangle" in types
        assert "mask" in types


# ── ROIManager ───────────────────────────────────────────────────────

class TestROIManager:
    def test_create_assigns_trace_id(self, roi_mgr):
        roi = roi_mgr.create("circle", (100, 200, 50), (1920, 1080), "test_node")
        assert roi.trace_id.startswith("roi_")

    def test_create_unknown_type_raises(self, roi_mgr):
        from core.roi.data import ROIError
        with pytest.raises(ROIError, match="Unknown ROI type"):
            roi_mgr.create("nonexistent", (100, 200, 50))

    def test_combine_union(self, roi_mgr):
        from core.roi.data import ROIData
        r1 = ROIData(roi_type="circle", data=(50, 50, 30), image_size=(200, 200))
        r2 = ROIData(roi_type="circle", data=(150, 150, 30), image_size=(200, 200))
        mask = roi_mgr.combine([r1, r2], (200, 200), mode="union")
        assert mask[50, 50]
        assert mask[150, 150]

    def test_combine_intersection(self, roi_mgr):
        from core.roi.data import ROIData
        r1 = ROIData(roi_type="rectangle", data=(0, 0, 100, 100), image_size=(200, 200))
        r2 = ROIData(roi_type="rectangle", data=(50, 50, 100, 100), image_size=(200, 200))
        mask = roi_mgr.combine([r1, r2], (200, 200), mode="intersection")
        assert mask[75, 75]  # in overlap
        assert not mask[25, 25]  # only in r1
        assert not mask[125, 125]  # only in r2

    def test_combine_difference(self, roi_mgr):
        from core.roi.data import ROIData
        r1 = ROIData(roi_type="rectangle", data=(0, 0, 100, 100), image_size=(200, 200))
        r2 = ROIData(roi_type="rectangle", data=(50, 50, 100, 100), image_size=(200, 200))
        mask = roi_mgr.combine([r1, r2], (200, 200), mode="difference")
        assert mask[25, 25]  # only in r1
        assert not mask[75, 75]  # in overlap
        assert not mask[125, 125]  # only in r2

    def test_combine_empty_returns_all_true(self, roi_mgr):
        mask = roi_mgr.combine([], (200, 200))
        assert mask.all()

    def test_apply_constraint_no_rois(self, roi_mgr):
        original = np.zeros((100, 200, 3), dtype=np.uint8)
        processed = np.ones((100, 200, 3), dtype=np.uint8) * 255
        result = roi_mgr.apply_constraint(original, processed, [])
        np.testing.assert_array_equal(result, processed)

    def test_apply_constraint_only_modifies_roi_region(self, roi_mgr):
        from core.roi.data import ROIData
        original = np.zeros((200, 200, 3), dtype=np.uint8)
        processed = np.ones((200, 200, 3), dtype=np.uint8) * 255
        roi = ROIData(roi_type="rectangle", data=(50, 50, 100, 100), image_size=(200, 200))
        result = roi_mgr.apply_constraint(original, processed, [roi])
        # Inside ROI: processed value
        assert result[100, 100, 0] == 255
        # Outside ROI: original value
        assert result[10, 10, 0] == 0

    def test_available_types(self, roi_mgr):
        types = roi_mgr.available_types()
        assert "circle" in types
        assert "polygon" in types


# ── ROITracer ────────────────────────────────────────────────────────

class TestROITracer:
    def test_query_returns_full_lifecycle(self, tracer):
        tid = tracer.begin("test_node", "circle")
        tracer.step(tid, "to_mask", "size=(200,200)")
        tracer.warn(tid, "test warning")
        tracer.end(tid, "created")
        entries = tracer.query(tid)
        assert len(entries) == 4
        assert entries[0].operation == "BEGIN"
        assert entries[1].operation == "to_mask"
        assert entries[2].operation == "WARN"
        assert entries[3].operation == "END"

    def test_query_by_source(self, tracer):
        tid1 = tracer.begin("node_a", "circle")
        tid2 = tracer.begin("node_b", "polygon")
        tracer.end(tid1, "ok")
        tracer.end(tid2, "ok")
        entries = tracer.query_by_source("node_a")
        assert all(e.source == "node_a" for e in entries)

    def test_dump_active(self, tracer):
        tid = tracer.begin("test_node", "circle")
        dump = tracer.dump_active()
        assert tid in dump
        tracer.end(tid, "ok")
        dump = tracer.dump_active()
        assert "No active" in dump


# ── ROISerializer ────────────────────────────────────────────────────

class TestROISerializer:
    def test_circle_save_load_roundtrip(self, roi_mgr):
        from core.roi.serializer import ROISerializer
        from core.roi.data import ROIData
        roi = roi_mgr.create("circle", (100, 200, 50), (1920, 1080), "test")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        ROISerializer.save(roi, path)
        loaded = ROISerializer.load(path)
        assert loaded.roi_type == "circle"
        assert loaded.data == (100, 200, 50)
        assert loaded.image_size == (1920, 1080)
        Path(path).unlink()

    def test_polygon_save_load_roundtrip(self, roi_mgr):
        from core.roi.serializer import ROISerializer
        from core.roi.data import ROIData
        vertices = [[10, 10], [100, 10], [50, 100]]
        roi = roi_mgr.create("polygon", vertices, (200, 200), "test")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        ROISerializer.save(roi, path)
        loaded = ROISerializer.load(path)
        assert loaded.roi_type == "polygon"
        assert np.array_equal(np.asarray(loaded.data), np.asarray(vertices))
        Path(path).unlink()

    def test_mask_save_load_roundtrip(self, roi_mgr):
        from core.roi.serializer import ROISerializer
        from core.roi.data import ROIData
        mask_data = np.zeros((100, 200), dtype=np.uint8)
        mask_data[20:80, 50:150] = 1
        roi = roi_mgr.create("mask", mask_data, (200, 100), "test")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        ROISerializer.save(roi, path)
        loaded = ROISerializer.load(path)
        assert loaded.roi_type == "mask"
        assert np.array_equal(np.asarray(loaded.data), mask_data)
        Path(path).unlink()

    def test_multiple_rois_save_load(self, roi_mgr):
        from core.roi.serializer import ROISerializer
        rois = [
            roi_mgr.create("circle", (100, 200, 50), (1920, 1080), "test"),
            roi_mgr.create("rectangle", (10, 20, 100, 50), (1920, 1080), "test"),
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        ROISerializer.save_rois(rois, path)
        loaded = ROISerializer.load_rois(path)
        assert len(loaded) == 2
        assert loaded[0].roi_type == "circle"
        assert loaded[1].roi_type == "rectangle"
        Path(path).unlink()


# ── Port Type ────────────────────────────────────────────────────────

class TestPortType:
    def test_roi_connects_to_roi(self):
        from core.node_base.port import Port, PortDefinition, PortDirection, PortType
        p1 = Port(PortDefinition("out", PortType.ROI, PortDirection.OUTPUT))
        p2 = Port(PortDefinition("in", PortType.ROI, PortDirection.INPUT))
        assert p1.can_connect(p2)
        assert p2.can_connect(p1)

    def test_roi_rejects_image(self):
        from core.node_base.port import Port, PortDefinition, PortDirection, PortType
        p_roi = Port(PortDefinition("out", PortType.ROI, PortDirection.OUTPUT))
        p_img = Port(PortDefinition("in", PortType.IMAGE, PortDirection.INPUT))
        assert not p_roi.can_connect(p_img)
        assert not p_img.can_connect(p_roi)

    def test_any_connects_to_roi(self):
        from core.node_base.port import Port, PortDefinition, PortDirection, PortType
        p_any = Port(PortDefinition("out", PortType.ANY, PortDirection.OUTPUT))
        p_roi = Port(PortDefinition("in", PortType.ROI, PortDirection.INPUT))
        assert p_any.can_connect(p_roi)
        assert p_roi.can_connect(p_any)

    def test_image_connects_to_image(self):
        from core.node_base.port import Port, PortDefinition, PortDirection, PortType
        p1 = Port(PortDefinition("out", PortType.IMAGE, PortDirection.OUTPUT))
        p2 = Port(PortDefinition("in", PortType.IMAGE, PortDirection.INPUT))
        assert p1.can_connect(p2)
