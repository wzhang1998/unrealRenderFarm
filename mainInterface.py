import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
import subprocess

class MainInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.request_manager_process = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        btn1 = QPushButton('Run requestManager.py', self)
        btn1.clicked.connect(self.run_request_manager)
        layout.addWidget(btn1)

        btn2 = QPushButton('Run requestSubmitter.py', self)
        btn2.clicked.connect(self.run_request_submitter)
        layout.addWidget(btn2)

        btn3 = QPushButton('Run requestWorker.py', self)
        btn3.clicked.connect(self.run_request_worker)
        layout.addWidget(btn3)

        self.setLayout(layout)
        self.setWindowTitle('Main Interface')
        self.show()

    def run_request_manager(self):
        self.request_manager_process = subprocess.Popen(['start', 'cmd', '/k', 'python requestManager.py'], shell=True)

    def run_request_submitter(self):
        subprocess.Popen(['start', 'cmd', '/k', 'python requestSubmitter.py'], shell=True)

    def run_request_worker(self):
        subprocess.Popen(['start', 'cmd', '/k', 'python requestWorker.py'], shell=True)

    def closeEvent(self, event):
        if self.request_manager_process:
            self.request_manager_process.terminate()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainInterface()
    sys.exit(app.exec_())