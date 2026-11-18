"""Repository layer. Public repository operations match the base UML diagram."""
from datetime import datetime, date
import json
import re
from src.infrastructure.database import password_hash


def _record(value):
    """Convert a UML data object or mapping to the repository's SQL field names."""
    raw = dict(value) if isinstance(value, dict) else vars(value)
    return {re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower(): val for key, val in raw.items()}


def _stored(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


class IRepository:
    _table_name = None
    _id_column = "id"

    def __init__(self, db):
        self._db = db

    def getById(self, id):
        if not self._table_name:
            raise NotImplementedError
        rows = self._db.query(f"SELECT * FROM {self._table_name} WHERE {self._id_column}=?", (id,))
        return dict(rows[0]) if rows else None

    def save(self, obj):
        if not self._table_name:
            raise NotImplementedError
        values = {k: _stored(v) for k, v in _record(obj).items()}
        # Hash the plain-text registration password BEFORE filtering fields against
        # the SQL schema. The users table stores password_hash, never password;
        # filtering first silently discarded password and caused NOT NULL failures.
        if self._table_name == "users" and "password" in values:
            plain_password = values.pop("password")
            values["password_hash"] = password_hash(str(plain_password))
        columns = {row[1] for row in self._db.query(f"PRAGMA table_info({self._table_name})")}
        values = {k: v for k, v in values.items() if k in columns}
        names = list(values)
        self._db.execute(
            f"INSERT OR REPLACE INTO {self._table_name} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
            [values[k] for k in names],
        )

    def delete(self, id):
        if not self._table_name:
            raise NotImplementedError
        self._db.execute(f"DELETE FROM {self._table_name} WHERE {self._id_column}=?", (id,))


class UserRepository(IRepository):
    _table_name = "users"

    def getUsersByRole(self, role):
        return [dict(r) for r in self._db.query("SELECT * FROM users WHERE role=? ORDER BY name", (role,))]

    def authenticateUser(self, email, password, role):
        """Authenticate by email/password and the role selected on the login screen."""
        row = self._db.query(
            "SELECT id,name,email,role FROM users WHERE lower(email)=lower(?) AND password_hash=? AND role=?",
            (email.strip(), password_hash(password), role),
        )
        return dict(row[0]) if row else None

    def createUser(self, user):
        """Create a user with an explicit password_hash column mapping.

        Registration must not rely on the generic IRepository.save field filter:
        the domain object calls the plain-text field `password`, while SQLite
        requires `password_hash`. Keep this mapping local and explicit so it
        also works with databases created by earlier project versions.
        """
        raw = _record(user)
        role_names = {
            "Agronomist": "Агроном",
            "CropScout": "Агроскаут",
            "Engineer": "Инженер-механизатор",
            "Analyst": "Аналитик",
            "GovernmentAgency": "Государственное / экологическое ведомство",
        }
        role = raw.get("role") or role_names.get(type(user).__name__, "")
        user_id = raw.get("id")
        name = raw.get("name")
        email = str(raw.get("email") or "").strip()
        plain_password = raw.get("password")
        if not all((user_id, name, email, plain_password, role)):
            raise ValueError("Для регистрации нужны ФИО, email, пароль и роль")
        hashed = password_hash(str(plain_password))
        # Explicit SQL prevents a missing password_hash when the generic save()
        # method receives an entity with a different field name.
        self._db.execute(
            "INSERT INTO users (id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            (str(user_id), str(name).strip(), email, hashed, role),
        )

    def updateUser(self, user):
        raw = _record(user)
        role_names = {
            "Agronomist": "Агроном", "CropScout": "Агроскаут",
            "Engineer": "Инженер-механизатор", "Analyst": "Аналитик",
            "GovernmentAgency": "Государственное / экологическое ведомство",
        }
        role = raw.get("role") or role_names.get(type(user).__name__, "")
        self._db.execute(
            "UPDATE users SET name=?,email=?,role=? WHERE id=?",
            (raw["name"], raw["email"], role, raw["id"]),
        )


class FieldRepository(IRepository):
    _table_name = "fields"
    def getFields(self):
        return [dict(r) for r in self._db.query("SELECT * FROM fields ORDER BY id")]

    def updateField(self, field):
        field = _record(field)
        self._db.execute("UPDATE fields SET coordinates=? WHERE id=?", (field["coordinates"], field["id"]))


class SensorRepository(IRepository):
    _table_name = "sensors"

    def getSensors(self):
        return [dict(r) for r in self._db.query("SELECT * FROM sensors ORDER BY id")]

    def registerSensor(self, sensor):
        sensor = _record(sensor)
        self._db.execute(
            "INSERT INTO sensors(id,type,coordinates,status,field_id,battery,last_fault) VALUES(?,?,?,?,?,?,?)",
            (sensor["id"], sensor["type"], sensor["coordinates"], sensor.get("status", "Работает"),
             sensor["field_id"], sensor.get("battery", 100), sensor.get("last_fault")),
        )

    def configureSensor(self, sensorId, newType, newCoords):
        self._db.execute("UPDATE sensors SET type=?,coordinates=? WHERE id=?", (newType, newCoords, sensorId))

    def setSensorStatus(self, sensorId, status):
        allowed={"Работает", "Выключен", "В ремонте", "Требует проверки", "Неисправен"}
        if status not in allowed:
            raise ValueError(f"Недопустимое состояние датчика: {status}")
        self._db.execute("UPDATE sensors SET status=? WHERE id=?", (status, sensorId))

    def reportFault(self, sensorId, faultDescription):
        now = datetime.now().isoformat(timespec="minutes")
        self._db.execute("UPDATE sensors SET status='Неисправен',last_fault=? WHERE id=?", (faultDescription, sensorId))
        import uuid
        self._db.execute("INSERT INTO equipment_events VALUES(?,?,?,?,?,?)",
                         (uuid.uuid4().hex, sensorId, "Неисправность", faultDescription, now, "Открыто"))

    def scheduleRepair(self, sensorId):
        now = datetime.now().isoformat(timespec="minutes")
        import uuid
        self._db.execute("INSERT INTO repair_orders VALUES(?,?,?,?,?)",
                         (uuid.uuid4().hex, sensorId, now, "Запланирован", "Плановое обслуживание датчика"))
        self._db.execute("UPDATE sensors SET status='Ремонт запланирован' WHERE id=?", (sensorId,))

    def getMachinery(self):
        return [dict(r) for r in self._db.query("SELECT * FROM machinery ORDER BY id")]

    def integrateSensor(self, sensorId, machineryId):
        self._db.execute("INSERT OR REPLACE INTO equipment_integrations VALUES(?,?,?)",
                         (sensorId, machineryId, datetime.now().isoformat(timespec="minutes")))

    def getSensorIntegrations(self):
        return [dict(r) for r in self._db.query(
            "SELECT i.sensor_id,i.machinery_id,i.linked_at,s.type sensor_type,m.name machinery_name "
            "FROM equipment_integrations i JOIN sensors s ON s.id=i.sensor_id "
            "JOIN machinery m ON m.id=i.machinery_id ORDER BY i.linked_at DESC") ]

    def getEquipmentEvents(self, sensorId=None):
        if sensorId:
            rows = self._db.query("SELECT * FROM equipment_events WHERE sensor_id=? ORDER BY created_at DESC", (sensorId,))
        else:
            rows = self._db.query("SELECT * FROM equipment_events ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    def getRepairOrders(self):
        return [dict(r) for r in self._db.query("SELECT * FROM repair_orders ORDER BY created_at DESC")]


class SensorReadingRepository(IRepository):
    _table_name = "sensor_readings"

    def getReadings(self, sensorId, period):
        sql = "SELECT r.*,s.field_id FROM sensor_readings r JOIN sensors s ON s.id=r.sensor_id WHERE 1=1"
        params = []
        if sensorId:
            sql += " AND r.sensor_id=?"; params.append(sensorId)
        if period:
            sql += " AND r.reading_time LIKE ?"; params.append(f"%{period}%")
        sql += " ORDER BY r.reading_time DESC"
        return [dict(r) for r in self._db.query(sql, params)]

    def getLatestByField(self, fieldId):
        return [dict(r) for r in self._db.query(
            "SELECT r.*,s.field_id FROM sensor_readings r JOIN sensors s ON s.id=r.sensor_id WHERE s.field_id=? ORDER BY r.reading_time DESC",
            (fieldId,),
        )]

    def saveReading(self, reading):
        reading = _record(reading)
        self._db.execute(
            "INSERT INTO sensor_readings VALUES(?,?,?,?,?)",
            (reading["id"], reading["type"], reading["value"], _stored(reading["reading_time"]), reading["sensor_id"]),
        )


class ProblemAreaRepository(IRepository):
    _table_name = "problem_areas"

    def getProblemAreas(self):
        return [dict(r) for r in self._db.query("SELECT * FROM problem_areas ORDER BY id")]

    def getByField(self, fieldId):
        return [dict(r) for r in self._db.query("SELECT * FROM problem_areas WHERE field_id=?", (fieldId,))]

    def registerProblem(self, area):
        area = _record(area)
        self._db.execute(
            "INSERT INTO problem_areas VALUES(?,?,?,?,?)",
            (area["id"], area["problem_type"], area["coordinates"], area["status"], area["field_id"]),
        )

    def updateStatus(self, id, status):
        self._db.execute("UPDATE problem_areas SET status=? WHERE id=?", (status, id))


class InspectionRepository(IRepository):
    _table_name = "inspections"

    def getInspections(self):
        return [dict(r) for r in self._db.query("SELECT * FROM inspections ORDER BY timestamp DESC")]

    def getByField(self, fieldId):
        return [dict(r) for r in self._db.query("SELECT * FROM inspections WHERE field_id=? ORDER BY timestamp DESC", (fieldId,))]

    def createInspection(self, inspection):
        inspection = _record(inspection)
        photos = _stored(inspection.get("photo_report", []))
        self._db.execute(
            "INSERT INTO inspections VALUES(?,?,?,?,?,?,?,?)",
            (inspection["id"], _stored(inspection["timestamp"]), inspection["coordinates"], inspection["description"],
             photos, inspection["field_id"], inspection["inspector_id"], inspection.get("problem_area_id")),
        )

    def updateInspection(self, inspection):
        inspection = _record(inspection)
        self._db.execute(
            "UPDATE inspections SET description=?,photo_report=? WHERE id=?",
            (inspection["description"], _stored(inspection.get("photo_report", [])), inspection["id"]),
        )


class TaskRepository(IRepository):
    _table_name = "tasks"

    def getTasksByStatus(self, status):
        sql = "SELECT t.*,p.problem_type,p.field_id,u.name executor_name FROM tasks t LEFT JOIN problem_areas p ON p.id=t.problem_area_id LEFT JOIN users u ON u.id=t.agronomist_id"
        params = ()
        if status and status != "Все":
            sql += " WHERE t.status=?"; params = (status,)
        return [dict(r) for r in self._db.query(sql + " ORDER BY deadline", params)]

    def createTask(self, task):
        task = _record(task)
        self._db.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?)",
            (task["id"], task["task_type"], task["status"], _stored(task["deadline"]), task["agronomist_id"], task.get("problem_area_id")),
        )

    def updateTask(self, task):
        task = _record(task)
        self._db.execute(
            "UPDATE tasks SET task_type=?,status=?,deadline=?,problem_area_id=? WHERE id=?",
            (task["task_type"], task["status"], _stored(task["deadline"]), task.get("problem_area_id"), task["id"]),
        )


class ReportRepository(IRepository):
    _table_name = "reports"

    def getById(self, id):
        rows = self._db.query(
            "SELECT r.*,u.name author_name FROM reports r LEFT JOIN users u ON u.id=r.author_id WHERE r.id=?",
            (id,),
        )
        return dict(rows[0]) if rows else None

    def getReports(self, period):
        rows = self._db.query("SELECT r.*,u.name author_name FROM reports r LEFT JOIN users u ON u.id=r.author_id ORDER BY r.rowid DESC")
        return [dict(r) for r in rows if not period or period.lower() in r["period"].lower()]

    def getAllReports(self):
        return [dict(r) for r in self._db.query("SELECT r.*,u.name author_name FROM reports r LEFT JOIN users u ON u.id=r.author_id ORDER BY r.rowid DESC")]

    def createReport(self, report):
        report = _record(report)
        field_ids = report.get("field_ids", [])
        if isinstance(field_ids, (list, tuple)):
            field_ids = ",".join(field_ids)
        self._db.execute(
            "INSERT INTO reports VALUES(?,?,?,?,?)",
            (report["id"], report["period"], report["content"], report.get("author_id", ""), field_ids),
        )
