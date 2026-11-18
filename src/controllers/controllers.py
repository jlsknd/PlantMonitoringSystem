"""Controller layer. Public operations and repository associations follow UML."""


class CropMonitoringController:
    def __init__(self, readingsRepo, zonesRepo, fieldsRepo):
        self.readingsRepo = readingsRepo
        self.zonesRepo = zonesRepo
        self.fieldsRepo = fieldsRepo

    def getReadingsByField(self, fieldId):
        return self.readingsRepo.getLatestByField(fieldId)

    def getFieldsOverview(self):
        return self.fieldsRepo.getFields()

    def getProblemAreas(self):
        return self.zonesRepo.getProblemAreas()

    def registerProblemArea(self, area):
        return self.zonesRepo.registerProblem(area)

    def updateProblemArea(self, id, status):
        return self.zonesRepo.updateStatus(id, status)


class AnalysisController:
    def __init__(self, readingsRepo, zonesRepo):
        self.readingsRepo = readingsRepo
        self.zonesRepo = zonesRepo

    def analyzeCurrentSituation(self):
        return None

    def detectAnomalies(self):
        return self.zonesRepo.getProblemAreas()

    def computeHealthIndex(self, fieldId):
        readings = self.readingsRepo.getLatestByField(fieldId)
        if not readings:
            return 0.0
        values = [float(item["value"]) for item in readings]
        return round(max(0.0, min(100.0, 100.0 - sum(abs(v - 60) for v in values) / len(values))), 1)

    def getAnalytics(self):
        return [self.zonesRepo.getProblemAreas()]


class EquipmentMonitoringController:
    def __init__(self, sensorsRepo):
        self.sensorsRepo = sensorsRepo

    def getSensors(self):
        return self.sensorsRepo.getSensors()

    def configureSensor(self, sensorId, newType, newCoords):
        return self.sensorsRepo.configureSensor(sensorId, newType, newCoords)

    def setSensorStatus(self, sensorId, status):
        return self.sensorsRepo.setSensorStatus(sensorId, status)

    def reportFault(self, sensorId, faultDescription):
        return self.sensorsRepo.reportFault(sensorId, faultDescription)

    def scheduleRepair(self, sensorId):
        return self.sensorsRepo.scheduleRepair(sensorId)

    def getMachinery(self):
        return self.sensorsRepo.getMachinery()

    def getEquipmentEvents(self, sensorId=None):
        return self.sensorsRepo.getEquipmentEvents(sensorId)

    def getRepairOrders(self):
        return self.sensorsRepo.getRepairOrders()

    def integrateSensor(self, sensorId, machineryId):
        return self.sensorsRepo.integrateSensor(sensorId, machineryId)

    def getSensorIntegrations(self):
        return self.sensorsRepo.getSensorIntegrations()


class InspectionController:
    def __init__(self, inspectionsRepo, zonesRepo):
        self.inspectionsRepo = inspectionsRepo
        self.zonesRepo = zonesRepo

    def getProblemZoneCoordinates(self):
        return self.zonesRepo.getProblemAreas()

    def registerInspection(self, inspection):
        return self.inspectionsRepo.createInspection(inspection)

    def getInspectionsByField(self, fieldId):
        return self.inspectionsRepo.getByField(fieldId)

    def updateInspection(self, inspection):
        return self.inspectionsRepo.updateInspection(inspection)


class TaskController:
    def __init__(self, tasksRepo, zonesRepo):
        self.tasksRepo = tasksRepo
        self.zonesRepo = zonesRepo

    def createTask(self, task):
        return self.tasksRepo.createTask(task)

    def updateTaskStatus(self, taskId, status):
        tasks = self.tasksRepo.getTasksByStatus("Все")
        task = next((item for item in tasks if item.get("id") == taskId), None)
        if task is None:
            return None
        task["status"] = status
        return self.tasksRepo.updateTask(task)

    def getPendingTasks(self, status="Новое"):
        return self.tasksRepo.getTasksByStatus(status)


class ReportController:
    def __init__(self, reportsRepo, readingsRepo):
        self.reportsRepo = reportsRepo
        self.readingsRepo = readingsRepo

    def generateReport(self, period, fieldIds, authorId=None):
        report_id = __import__("uuid").uuid4().hex[:8].upper()
        selected_fields = list(fieldIds) if fieldIds else []
        reading_rows = []
        for field_id in selected_fields:
            reading_rows.extend(self.readingsRepo.getLatestByField(field_id))
        if " — " in str(period):
            start, end = [part.strip()[:10] for part in str(period).split(" — ", 1)]
            reading_rows = [r for r in reading_rows if start <= str(r.get("reading_time", ""))[:10] <= end]
        content = "СВОДНЫЙ ОТЧЁТ ПО МОНИТОРИНГУ ПОЛЕЙ\n"
        content += "Период: " + str(period) + "\n"
        content += "Поля: " + (", ".join(selected_fields) if selected_fields else "все поля") + "\n"
        content += "Количество показаний: " + str(len(reading_rows)) + "\n"
        if reading_rows:
            by_type = {}
            for item in reading_rows:
                key = item.get("type", "Показатель")
                by_type.setdefault(key, []).append(float(item.get("value", 0)))
            content += "\nСРЕДНИЕ ЗНАЧЕНИЯ ПО ПОКАЗАТЕЛЯМ\n"
            for metric, values in sorted(by_type.items()):
                content += f"{metric}: {sum(values) / len(values):.2f} (измерений: {len(values)})\n"
        report = {
            "id": report_id,
            "period": period,
            "content": content,
            "author_id": authorId,
            "field_ids": ",".join(selected_fields),
        }
        self.reportsRepo.createReport(report)
        return report

    def getReports(self, period):
        return self.reportsRepo.getReports(period)

    def exportReport(self, reportId, format, outputPath=None):
        report = self.reportsRepo.getById(reportId)
        if report is None:
            raise ValueError("Отчёт не найден")
        from pathlib import Path
        import csv
        target = Path(outputPath) if outputPath else Path(f"report_{reportId}.{format.lower()}")
        fmt = format.lower().lstrip(".")
        if fmt == "pdf":
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.utils import simpleSplit
            import os
            font_candidates = [
                "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/times.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            font_path = next((f for f in font_candidates if os.path.exists(f)), None)
            font_name = "Helvetica"
            if font_path:
                try:
                    pdfmetrics.registerFont(TTFont("PlantFont", font_path)); font_name = "PlantFont"
                except Exception:
                    pass
            c = canvas.Canvas(str(target), pagesize=A4); width, height = A4; y = height - 55
            c.setFont(font_name, 16); c.drawString(48, y, f"Отчёт {report['id']}"); y -= 30
            c.setFont(font_name, 10)
            for line in [f"Период: {report['period']}", f"Автор: {report.get('author_name') or '—'}", "", *report['content'].splitlines()]:
                for wrapped in simpleSplit(line, font_name, 10, width - 96):
                    if y < 55: c.showPage(); y = height - 55; c.setFont(font_name, 10)
                    c.drawString(48, y, wrapped); y -= 16
            c.save(); return str(target)
        if fmt in ("xlsx", "excel"):
            from openpyxl import Workbook
            wb = Workbook(); ws = wb.active; ws.title = "Отчёт"
            ws.append(["Показатель", "Значение"]); ws.append(["ID", report['id']]); ws.append(["Период", report['period']])
            ws.append(["Автор", report.get("author_name") or "—"]); ws.append(["Содержание", report['content']])
            ws.column_dimensions['A'].width = 22; ws.column_dimensions['B'].width = 100
            wb.save(target); return str(target)
        if fmt == "csv":
            with target.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream, delimiter=";"); writer.writerow(["ID", "Период", "Автор", "Содержание"])
                writer.writerow([report['id'], report['period'], report.get('author_name') or "—", report['content']])
            return str(target)
        if fmt == "txt":
            target.write_text(f"Отчёт {report['id']}\nПериод: {report['period']}\nАвтор: {report.get('author_name') or '—'}\n\n{report['content']}", encoding="utf-8")
            return str(target)
        raise ValueError(f"Неподдерживаемый формат экспорта: {format}")
