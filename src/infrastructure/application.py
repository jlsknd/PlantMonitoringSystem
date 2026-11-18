"""Desktop application composition root matching PlantMonitoringApplication UML."""
from src.infrastructure.dependency_container import DependencyContainer
from src.infrastructure.database import Database
from src.controllers.controllers import (
    CropMonitoringController, AnalysisController, EquipmentMonitoringController,
    InspectionController, TaskController, ReportController,
)
from src.model.repositories import UserRepository


class PlantMonitoringApplication:
    def __init__(self):
        self.container = self.configure()
        self.controllers = [
            self.container.createController(CropMonitoringController),
            self.container.createController(AnalysisController),
            self.container.createController(EquipmentMonitoringController),
            self.container.createController(InspectionController),
            self.container.createController(TaskController),
            self.container.createController(ReportController),
        ]
        self.views = []

    def main(self, args):
        return self.run()

    def configure(self):
        return DependencyContainer()

    def run(self):
        from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
        from src.view.windows import LoginWindow, RegistrationWindow, MainShell, APP_QSS
        qt = QApplication.instance() or QApplication([])
        qt.setApplicationName("Система мониторинга состояния растений")
        qt.setStyleSheet(APP_QSS)
        window = QMainWindow()
        window.setWindowTitle("Система мониторинга состояния растений")
        window.resize(1100, 760)
        stack = QStackedWidget()
        window.setCentralWidget(stack)
        current = {"main": None}

        def open_login():
            stack.setCurrentWidget(login_view)

        def open_registration():
            stack.setCurrentWidget(registration_view)

        def open_main(user):
            if current["main"] is not None:
                stack.removeWidget(current["main"])
                current["main"].deleteLater()
            current["main"] = MainShell(self.container, user, open_login)
            self.views.append(current["main"])
            stack.addWidget(current["main"])
            stack.setCurrentWidget(current["main"])

        user_repository = self.container.resolve(UserRepository)
        login_view = LoginWindow(user_repository, open_main, open_registration)
        registration_view = RegistrationWindow(user_repository, open_login)
        self.views.extend([login_view, registration_view])
        stack.addWidget(login_view)
        stack.addWidget(registration_view)
        stack.setCurrentWidget(login_view)
        window.show()
        try:
            return qt.exec()
        finally:
            self.shutdown()

    def shutdown(self):
        self.container.resolve(Database).close()
