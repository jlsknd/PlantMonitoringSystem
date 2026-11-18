"""Dependency container. Its public API matches the UML class diagram."""
from src.infrastructure.database import Database
from src.model.repositories import (
    UserRepository, FieldRepository, SensorRepository, SensorReadingRepository,
    ProblemAreaRepository, InspectionRepository, TaskRepository, ReportRepository,
)
from src.controllers.controllers import (
    CropMonitoringController, AnalysisController, EquipmentMonitoringController,
    InspectionController, TaskController, ReportController,
)


class DependencyContainer:
    def __init__(self):
        self.registry = {}
        db = Database()
        self.registry[Database] = db

        # Repository instances follow the associations shown in the UML.
        repositories = {
            UserRepository: UserRepository(db),
            FieldRepository: FieldRepository(db),
            SensorRepository: SensorRepository(db),
            SensorReadingRepository: SensorReadingRepository(db),
            ProblemAreaRepository: ProblemAreaRepository(db),
            InspectionRepository: InspectionRepository(db),
            TaskRepository: TaskRepository(db),
            ReportRepository: ReportRepository(db),
        }
        self.registry.update(repositories)

        controllers = {
            CropMonitoringController: CropMonitoringController(
                repositories[SensorReadingRepository],
                repositories[ProblemAreaRepository],
                repositories[FieldRepository],
            ),
            AnalysisController: AnalysisController(
                repositories[SensorReadingRepository],
                repositories[ProblemAreaRepository],
            ),
            EquipmentMonitoringController: EquipmentMonitoringController(
                repositories[SensorRepository],
            ),
            InspectionController: InspectionController(
                repositories[InspectionRepository],
                repositories[ProblemAreaRepository],
            ),
            TaskController: TaskController(
                repositories[TaskRepository],
                repositories[ProblemAreaRepository],
            ),
            ReportController: ReportController(
                repositories[ReportRepository],
                repositories[SensorReadingRepository],
            ),
        }
        self.registry.update(controllers)

    def register(self, iface, impl):
        self.registry[iface] = impl

    def resolve(self, iface):
        implementation = self.registry.get(iface)
        if implementation is None:
            raise KeyError(f"Dependency is not registered: {iface}")
        if isinstance(implementation, type):
            return implementation()
        return implementation

    def createRepository(self, type):
        return type(self.resolve(Database))

    def createController(self, type):
        instance = self.registry.get(type)
        if instance is None:
            raise KeyError(f"Controller is not registered: {type}")
        return instance

    def createView(self, type):
        instance = self.registry.get(type)
        if instance is not None:
            return instance
        return type()
