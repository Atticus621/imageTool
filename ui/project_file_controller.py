"""Project file operations controller.

Extracted from MainWindow to eliminate the triplicated "save modified?"
prompt and isolate project I/O from window shell concerns.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QFileDialog

from core.logger import logger
from core.config import config


class ProjectFileController(QObject):
    """Handles all project file operations: new, open, save, save-as, template.

    Owns the "save modified?" prompt flow so it isn't duplicated across
    three different call sites in MainWindow.

    Signals:
        status_message(str)     → update the status bar
        title_changed(str)      → update the window title
        project_cleared()       → project was cleared (new / loaded)
    """

    status_message = Signal(str)
    title_changed = Signal(str)
    project_cleared = Signal()

    def __init__(self, project_system, parent_window=None):
        super().__init__()
        self._project = project_system
        self._window = parent_window  # for dialog parenting

    # ── public helpers ──────────────────────────────────────────────────

    @property
    def is_modified(self) -> bool:
        return self._project.is_modified if self._project else False

    @property
    def has_project(self) -> bool:
        return self._project.has_project if self._project else False

    def prompt_save_changes(self) -> str:
        """Ask user to save, discard, or cancel.  Returns 'save'/'discard'/'cancel'."""
        if not self._project.is_modified:
            return "discard"
        reply = QMessageBox.question(
            self._window,
            "保存项目",
            "当前项目已修改，是否保存？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return "save"
        elif reply == QMessageBox.StandardButton.Discard:
            return "discard"
        return "cancel"

    # ── project operations ──────────────────────────────────────────────

    def new_project(self) -> bool:
        """Create a new project, prompting to save if modified.  Returns True
        if the user proceeded (new project created), False if cancelled."""
        action = self.prompt_save_changes()
        if action == "cancel":
            return False
        if action == "save" and not self.save_project():
            return False

        self._project.new_project()
        self.status_message.emit("新项目已创建")
        self.title_changed.emit("ImageTools")
        self.project_cleared.emit()
        logger.info("New project created")
        return True

    def open_project(self) -> bool:
        """Open an existing project file.  Returns True if a project was loaded."""
        action = self.prompt_save_changes()
        if action == "cancel":
            return False
        if action == "save" and not self.save_project():
            return False

        path, _ = QFileDialog.getOpenFileName(
            self._window, "打开项目文件", "",
            "ImageTools 项目 (*.itproj);;所有文件 (*)",
        )
        if not path:
            return False

        project_path = Path(path)

        # Check for auto-save recovery
        if self._project.check_autosave(project_path):
            from ui.dialogs import AutoSaveRecoveryDialog
            dialog = AutoSaveRecoveryDialog(
                project_path,
                project_path.with_suffix(project_path.suffix + "~"),
                self._window,
            )
            dialog.exec()
            if dialog.should_recover:
                if self._project.recover_autosave(project_path):
                    self.status_message.emit("已恢复自动保存的项目")
                    self._emit_title()
                    self.project_cleared.emit()
                    return True

        if self._project.load_project(project_path):
            self.status_message.emit(f"已加载: {project_path.name}")
            self._emit_title()
            self.project_cleared.emit()
            return True

        QMessageBox.warning(
            self._window, "加载失败",
            f"无法加载项目文件:\n{project_path}",
        )
        return False

    def save_project(self) -> bool:
        """Save the current project. Returns True if saved."""
        if self._project.current_path:
            if self._project.save_project():
                self.status_message.emit("项目已保存")
                self._emit_title()
                return True
            QMessageBox.warning(self._window, "保存失败", "无法保存项目文件")
            return False
        return self.save_project_as()

    def save_project_as(self) -> bool:
        """Save to a new file. Returns True if saved."""
        from ui.dialogs import SaveDialog

        if self._project.current_project is None:
            self._project.new_project(clear_graph=False)

        project = self._project.current_project
        dialog = SaveDialog(
            self._window,
            project_name=project.metadata.name if project else "",
        )
        if dialog.exec() != SaveDialog.DialogCode.Accepted:
            return False

        if project:
            project.metadata.name = dialog.project_name
            project.metadata.description = dialog.description
            project.metadata.author = dialog.author
            project.metadata.tags = dialog.tags

        default_name = dialog.project_name or "未命名项目"
        path, _ = QFileDialog.getSaveFileName(
            self._window, "保存项目文件", f"{default_name}.itproj",
            "ImageTools 项目 (*.itproj);;所有文件 (*)",
        )
        if not path:
            return False

        save_path = Path(path)
        if save_path.suffix != ".itproj":
            save_path = save_path.with_suffix(".itproj")

        if self._project.save_project(save_path):
            self.status_message.emit(f"项目已保存: {save_path.name}")
            self._emit_title()
            return True

        QMessageBox.warning(self._window, "保存失败", "无法保存项目文件")
        return False

    def save_as_template(self):
        """Save current project as a template."""
        if not self._project.has_project:
            QMessageBox.information(self._window, "提示", "没有打开的项目")
            return

        from ui.dialogs import SaveDialog
        dialog = SaveDialog(self._window)
        dialog.setWindowTitle("保存为模板")
        if dialog.exec() != SaveDialog.DialogCode.Accepted:
            return
        if not dialog.project_name:
            QMessageBox.warning(self._window, "错误", "请输入模板名称")
            return

        template = self._project.save_as_template(
            dialog.project_name, dialog.description,
        )
        if template:
            QMessageBox.information(
                self._window, "模板已保存",
                f"模板 '{dialog.project_name}' 已保存",
            )
        else:
            QMessageBox.warning(self._window, "保存失败", "无法保存模板")

    def handle_close(self, event) -> bool:
        """Handle window close event. Returns True if close should proceed."""
        action = self.prompt_save_changes()
        if action == "cancel":
            event.ignore()
            return False
        if action == "save" and not self.save_project():
            event.ignore()
            return False
        self._project.disable_autosave()
        event.accept()
        return True

    def update_window_title(self):
        """Delegate for MainWindow.setWindowTitle."""
        self._emit_title()

    # ── internal ─────────────────────────────────────────────────────────

    def _emit_title(self):
        base = "ImageTools"
        if self._project.has_project:
            name = self._project.current_project.metadata.name
            self.title_changed.emit(f"{name} - {base}")
        else:
            self.title_changed.emit(base)
