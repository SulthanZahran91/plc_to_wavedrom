
from PyQt6.QtWidgets import QTableView, QApplication, QMenu
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import  QAction

class CopyPasteTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # sane defaults for cell selection
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        # context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # ---- Copy / Paste core ----
    def copy_selection(self):
        sm = self.selectionModel()
        if not sm or not sm.hasSelection():
            return
        # group indexes by row, sorted
        indexes = sorted(sm.selectedIndexes(), key=lambda ix: (ix.row(), ix.column()))
        if not indexes:
            return

        rows = {}
        for ix in indexes:
            rows.setdefault(ix.row(), []).append(ix)

        lines = []
        for r in sorted(rows.keys()):
            row_cells = sorted(rows[r], key=lambda ix: ix.column())
            vals = []
            for ix in row_cells:
                v = self.model().data(ix, Qt.ItemDataRole.DisplayRole)
                if v is None:
                    v = ""
                # basic escaping for tabs/newlines
                vals.append(str(v).replace("\t", " ").replace("\n", " "))
            lines.append("\t".join(vals))

        QApplication.clipboard().setText("\n".join(lines))

    # def paste_from_clipboard(self):
    #     text = QApplication.clipboard().text()
    #     if not text:
    #         return

    #     model = self.model()
    #     if model is None:
    #         return

    #     start_ix: QModelIndex = self.currentIndex()
    #     if not start_ix.isValid():
    #         # fall back to (0,0)
    #         start_row, start_col = 0, 0
    #     else:
    #         start_row, start_col = start_ix.row(), start_ix.column()

    #     # parse TSV/CSV-ish (tabs preferred; split on '\t' then '\n')
    #     rows = [line for line in text.splitlines() if line != ""]
    #     matrix = [r.split("\t") for r in rows]
    #     nrows = len(matrix)
    #     ncols = max(len(r) for r in matrix) if nrows else 0

    #     # Optionally grow the model if it supports insertRows/insertColumns
    #     # (comment out if your model is fixed size)
    #     target_rows_needed = start_row + nrows
    #     target_cols_needed = start_col + ncols
    #     try:
    #         if target_rows_needed > model.rowCount():
    #             model.insertRows(model.rowCount(), target_rows_needed - model.rowCount())
    #     except Exception:
    #         pass
    #     try:
    #         if target_cols_needed > model.columnCount():
    #             model.insertColumns(model.columnCount(), target_cols_needed - model.columnCount())
    #     except Exception:
    #         pass

    #     # write values
    #     for r in range(nrows):
    #         for c in range(len(matrix[r])):
    #             row = start_row + r
    #             col = start_col + c
    #             if 0 <= row < model.rowCount() and 0 <= col < model.columnCount():
    #                 ix = model.index(row, col)
    #                 # only set if editable
    #                 if model.flags(ix) & Qt.ItemFlag.ItemIsEditable:
    #                     model.setData(ix, matrix[r][c], Qt.ItemDataRole.EditRole)

    # ---- Shortcuts ----
    def keyPressEvent(self, e):
        if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_C:
            self.copy_selection()
            return
        # if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_V:
        #     self.paste_from_clipboard()
        #     return
        super().keyPressEvent(e)

    # ---- Context Menu ----
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        act_copy = QAction("Copy", self)
        # act_paste = QAction("Paste", self)
        act_copy.triggered.connect(self.copy_selection)
        # act_paste.triggered.connect(self.paste_from_clipboard)
        menu.addAction(act_copy)
        # menu.addAction(act_paste)
        menu.exec(self.viewport().mapToGlobal(pos))
