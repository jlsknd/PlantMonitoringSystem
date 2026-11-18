"""View interfaces and BaseView exactly as named in the class diagram."""


class IView:
    def render(self, data):
        raise NotImplementedError

    def update(self, data):
        raise NotImplementedError


class ICropMonitoringView(IView):
    def showFieldMap(self, fields, zones):
        raise NotImplementedError

    def highlightProblemAreas(self, zones):
        raise NotImplementedError

    def showReadings(self, readings):
        raise NotImplementedError


class IEquipmentMonitoringView(IView):
    def showSensorStatus(self, sensors):
        raise NotImplementedError

    def showFaultAlert(self, sensorId, description):
        raise NotImplementedError


class IInspectionView(IView):
    def showZoneCoordinates(self, zones):
        raise NotImplementedError

    def submitInspectionForm(self, inspection):
        raise NotImplementedError


class ITaskView(IView):
    def showTasks(self, tasks):
        raise NotImplementedError

    def showTaskForm(self):
        raise NotImplementedError


class IReportView(IView):
    def showReport(self, report):
        raise NotImplementedError

    def exportReport(self, report, format):
        raise NotImplementedError


class BaseView(IView):
    def __init__(self, viewId=""):
        self.viewId = viewId

    def render(self, data):
        self.update(data)

    def update(self, data):
        return None
