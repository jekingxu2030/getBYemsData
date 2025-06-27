from PyQt5.QtWidgets import QApplication
import sys
from ui_window import WebSocketClient

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebSocketClient()
    window.show()
    sys.exit(app.exec_())
