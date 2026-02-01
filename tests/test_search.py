from ui.search import SearchApp
from PySide6.QtWidgets import QApplication
import sys
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


app = QApplication(sys.argv)

def test_live_search():
    w = SearchApp()

    w.name_edit.setText("Ali")
    w.search()

    assert w.table.rowCount() >= 1