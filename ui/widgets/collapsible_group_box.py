"""Reusable collapsible QGroupBox widget.

A QGroupBox with a checkbox toggle that shows/hides its contents.
Default state is collapsed (unchecked).
"""

from PySide6.QtWidgets import QGroupBox


class CollapsibleGroupBox(QGroupBox):
    """A QGroupBox that collapses/expands its children when toggled.

    Usage::

        group = CollapsibleGroupBox("标题")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("内容…"))
        group.finalize()
    """

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self._on_toggled)

    def finalize(self):
        """Sync visibility after layout is built. Call once after adding
        all child widgets."""
        self._apply_visibility(self.isChecked())

    def _on_toggled(self, checked: bool):
        self._apply_visibility(checked)

    def _apply_visibility(self, visible: bool):
        layout = self.layout()
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(visible)
