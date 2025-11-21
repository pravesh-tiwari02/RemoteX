"""

    License: Apache License 2.0
    More information about the LICENSE on the LICENSE file in the root directory of the project.
"""

import json
import os.path
import socket
from typing import Optional

from PyQt6.QtCore import QSettings, QSize, Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QKeyEvent
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
                             QWidget)

import remotex_viewer.remotex as remotex

import remotex_viewer.ui.dialogs as remotex_dialogs
import remotex_viewer.ui.forms as remotex_forms
import remotex_viewer.ui.utilities as utilities


class ConnectWindow(utilities.QCenteredMainWindow):
    """ Connect Window to establish a connection to the server """

    def __init__(self) -> None:
        super().__init__()

        self.__connect_thread: Optional[remotex.ConnectThread] = None
        self.__connecting_dialog: Optional[remotex_dialogs.ConnectingDialog] = None
        self.desktop_window: Optional[remotex_forms.DesktopWindow] = None
        self.session: Optional[remotex.Session] = None

        self.setWindowTitle(f"{remotex.APP_DISPLAY_NAME} :: Connect")

        self.setWindowFlags(
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Setup Main Layout (Core Layout)
        core_layout = QVBoxLayout()
        self.central_widget.setLayout(core_layout)

        # Setup Form Layout (Containing both Logo and Inputs)
        form_layout = QHBoxLayout()
        core_layout.addLayout(form_layout)

        # Logo
        icon = QLabel(self)
        icon.setPixmap(QIcon(remotex.APP_ICON).pixmap(QSize(96, 96)))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(icon)

        # Form Inputs
        form_input_layout = QVBoxLayout()
        form_layout.addLayout(form_input_layout)

        # Server Address Form Input
        self.server_address_label = QLabel("Server Address / Port:")
        form_input_layout.addWidget(self.server_address_label)

        server_address_layout = QHBoxLayout()

        self.server_address_input = QLineEdit()
        self.server_address_input.setText("127.0.0.1")
        server_address_layout.addWidget(self.server_address_input)

        separator_label = QLabel(":")
        server_address_layout.addWidget(separator_label)

        self.server_port_input = QSpinBox()
        self.server_port_input.setMinimum(0)
        self.server_port_input.setMaximum(65535)
        self.server_port_input.setValue(2801)
        server_address_layout.addWidget(self.server_port_input)

        server_address_layout.setStretch(0, 5)
        server_address_layout.setStretch(1, 0)
        server_address_layout.setStretch(2, 2)

        form_input_layout.addLayout(server_address_layout)

        form_input_layout.addSpacing(4)

        # Password Form Input
        self.password_label = QLabel("Password:")
        form_input_layout.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form_input_layout.addWidget(self.password_input)

        # Give Breath to Action Buttons
        form_input_layout.addSpacing(6)

        # Action Buttons
        self.about_button = QPushButton("About")
        self.about_button.clicked.connect(self.show_about_dialog)

        self.options_button = QPushButton("Options")
        self.options_button.clicked.connect(lambda: remotex_dialogs.OptionsDialog(self).exec())

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.submit_form)
        self.connect_button.setDefault(True)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.about_button)
        action_layout.addWidget(self.options_button)
        action_layout.addWidget(self.connect_button)

        core_layout.addLayout(action_layout)

        # Read Default Settings: Mostly for development purposes, until custom profiles are implemented
        self.read_default()

        self.adjust_size()

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        """ Handle certain key events like ESC to close the window or ENTER to submit default action """
        if event is None:
            return

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.submit_form()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()

        super().keyPressEvent(event)

    def read_default(self) -> None:
        """ Read default settings from the default.json file """
        if not os.path.isfile(remotex.DEFAULT_JSON):
            return

        with open(remotex.DEFAULT_JSON, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return

            if "use" in data and data["use"] is False:
                return

            if "server_address" in data:
                self.server_address_input.setText(data["server_address"])

            if "server_port" in data:
                self.server_port_input.setValue(data["server_port"])

            if "server_password" in data:
                self.password_input.setText(data["server_password"])

    def submit_form(self) -> None:
        """ Validate the form and submit it """
        try:
            # Check if the ip/hostname is valid
            hostname = self.server_address_input.text()
            try:
                if socket.gethostbyname(hostname) == hostname:
                    pass
            except socket.gaierror:
                self.server_address_input.setFocus()
                raise Exception("Invalid hostname or IP address.")

            # Check password input
            if len(self.password_input.text().strip()) == 0:
                self.password_input.setFocus()
                raise Exception("Password field cannot be empty.")

            # Attempt connection
            self.__connect_thread = remotex.ConnectThread(
                self.server_address_input.text(),
                self.server_port_input.value(),
                self.password_input.text(),
            )

            self.__connect_thread.thread_started.connect(self.connect_thread_started)
            self.__connect_thread.session_error.connect(self.session_error)
            self.__connect_thread.thread_finished.connect(self.connect_thread_finished)
            self.__connect_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "Form Error", str(e))

    def adjust_size(self) -> None:
        self.setFixedSize(350, self.sizeHint().height())

    def show_about_dialog(self) -> None:
        about_window = remotex_dialogs.AboutDialog(self)
        about_window.exec()

    @pyqtSlot(str)
    def session_error(self, error_message: str) -> None:
        QMessageBox.critical(self, "Error", error_message)

    @pyqtSlot()
    def connect_thread_started(self) -> None:
        self.__connecting_dialog = remotex_dialogs.ConnectingDialog(self)
        self.__connecting_dialog.exec()

    @pyqtSlot(object)
    def connect_thread_finished(self, session: Optional[remotex.Session] = None) -> None:
        # Close the connecting form if it is still open
        if self.__connecting_dialog is not None and self.__connecting_dialog.isVisible():
            self.__connecting_dialog.close()

        if session is None:
            return

        self.session = session

        # Show the Remote Desktop Window
        self.desktop_window = remotex_forms.DesktopWindow(self, self.session)
        self.desktop_window.show()
