"""Tests for EventGuard."""

import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QInputEvent
from PySide6.QtCore import QEvent


class FakeEvent:
    """Minimal event mock for testing EventGuard."""

    def __init__(self, button=Qt.MouseButton.LeftButton):
        self._button = button
        self._accepted = False

    def button(self):
        return self._button

    def accept(self):
        self._accepted = True

    @property
    def isAccepted(self):
        return self._accepted


class TestEventGuard:
    """Test event interception state machine."""

    def test_initial_state(self, event_guard):
        """Initial state should be IDLE."""
        assert not event_guard.is_drawing

    def test_left_press_enters_drawing(self, event_guard):
        """Left button press should enter DRAWING state."""
        event = FakeEvent(Qt.MouseButton.LeftButton)
        result = event_guard.on_press(event)
        assert result is True
        assert event_guard.is_drawing
        assert event._accepted

    def test_right_press_not_intercepted(self, event_guard):
        """Right button press should not be intercepted."""
        event = FakeEvent(Qt.MouseButton.RightButton)
        result = event_guard.on_press(event)
        assert result is False
        assert not event_guard.is_drawing

    def test_move_intercepted_while_drawing(self, event_guard):
        """Move events should be intercepted while drawing."""
        # Enter drawing state
        event_guard.on_press(FakeEvent(Qt.MouseButton.LeftButton))

        # Move should be intercepted
        event = FakeEvent()
        result = event_guard.on_move(event)
        assert result is True
        assert event._accepted

    def test_move_not_intercepted_when_idle(self, event_guard):
        """Move events should not be intercepted when idle."""
        event = FakeEvent()
        result = event_guard.on_move(event)
        assert result is False
        assert not event._accepted

    def test_release_enters_consumed(self, event_guard):
        """Release after press should enter CONSUMED state."""
        event_guard.on_press(FakeEvent(Qt.MouseButton.LeftButton))

        event = FakeEvent(Qt.MouseButton.LeftButton)
        result = event_guard.on_release(event)
        assert result is True
        assert not event_guard.is_drawing  # No longer drawing
        assert event._accepted

    def test_move_intercepted_when_consumed(self, event_guard):
        """Move events should be intercepted in CONSUMED state."""
        event_guard.on_press(FakeEvent(Qt.MouseButton.LeftButton))
        event_guard.on_release(FakeEvent(Qt.MouseButton.LeftButton))

        # Now in CONSUMED state
        event = FakeEvent()
        result = event_guard.on_move(event)
        assert result is True
        assert event._accepted

    def test_leave_resets_to_idle(self, event_guard):
        """Leave event should reset to IDLE."""
        event_guard.on_press(FakeEvent(Qt.MouseButton.LeftButton))
        assert event_guard.is_drawing

        event_guard.on_leave()
        assert not event_guard.is_drawing

    def test_full_drawing_cycle(self, event_guard):
        """Test complete drawing cycle: IDLE → DRAWING → CONSUMED → IDLE."""
        # IDLE → DRAWING
        event_guard.on_press(FakeEvent(Qt.MouseButton.LeftButton))
        assert event_guard.is_drawing

        # Move while drawing
        event_guard.on_move(FakeEvent())
        assert event_guard.is_drawing

        # DRAWING → CONSUMED
        event_guard.on_release(FakeEvent(Qt.MouseButton.LeftButton))
        assert not event_guard.is_drawing

        # Move while consumed (still intercepted)
        event = FakeEvent()
        result = event_guard.on_move(event)
        assert result is True

        # Leave → IDLE
        event_guard.on_leave()

        # Move now not intercepted
        event = FakeEvent()
        result = event_guard.on_move(event)
        assert result is False
