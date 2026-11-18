from pathlib import Path
import sqlite3, hashlib, uuid, math
from datetime import datetime, timedelta

ROLES = ("Агроном", "Агроскаут", "Инженер-механизатор", "Аналитик", "Государственное / экологическое ведомство")

def password_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

class Database:
    """SQLite local profile; repository API isolates storage so PostgreSQL can replace it."""
    def __init__(self, path=None):
        root = Path(__file__).resolve().parents[2]
        self.path = Path(path) if path else root / "database" / "plant_monitoring.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.initialize(); self.seed_demo_data()
    def execute(self, sql, params=()):
        cur = self.connection.execute(sql, params); self.connection.commit(); return cur
    def query(self, sql, params=()): return self.connection.execute(sql, params).fetchall()
    def initialize(self):
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fields(id TEXT PRIMARY KEY,coordinates TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sensors(id TEXT PRIMARY KEY,type TEXT NOT NULL,coordinates TEXT,status TEXT NOT NULL,field_id TEXT NOT NULL REFERENCES fields(id));
        CREATE TABLE IF NOT EXISTS sensor_readings(id TEXT PRIMARY KEY,type TEXT NOT NULL,value REAL NOT NULL,reading_time TEXT NOT NULL,sensor_id TEXT NOT NULL REFERENCES sensors(id));
        CREATE TABLE IF NOT EXISTS problem_areas(id TEXT PRIMARY KEY,problem_type TEXT NOT NULL,coordinates TEXT,status TEXT NOT NULL,field_id TEXT NOT NULL REFERENCES fields(id));
        CREATE TABLE IF NOT EXISTS inspections(id TEXT PRIMARY KEY,timestamp TEXT NOT NULL,coordinates TEXT,description TEXT,photo_report TEXT,field_id TEXT NOT NULL REFERENCES fields(id),inspector_id TEXT NOT NULL REFERENCES users(id),problem_area_id TEXT REFERENCES problem_areas(id));
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,task_type TEXT NOT NULL,status TEXT NOT NULL,deadline TEXT,agronomist_id TEXT NOT NULL REFERENCES users(id),problem_area_id TEXT REFERENCES problem_areas(id));
        CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,period TEXT NOT NULL,content TEXT NOT NULL,author_id TEXT NOT NULL REFERENCES users(id),field_ids TEXT);
        CREATE TABLE IF NOT EXISTS equipment_events(id TEXT PRIMARY KEY,sensor_id TEXT NOT NULL REFERENCES sensors(id),event_type TEXT NOT NULL,description TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS repair_orders(id TEXT PRIMARY KEY,sensor_id TEXT NOT NULL REFERENCES sensors(id),created_at TEXT NOT NULL,status TEXT NOT NULL,description TEXT);
        CREATE TABLE IF NOT EXISTS machinery(id TEXT PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,gps TEXT,status TEXT,fuel REAL);
        CREATE TABLE IF NOT EXISTS equipment_integrations(sensor_id TEXT NOT NULL REFERENCES sensors(id),machinery_id TEXT NOT NULL REFERENCES machinery(id),linked_at TEXT NOT NULL,PRIMARY KEY(sensor_id,machinery_id));
        CREATE INDEX IF NOT EXISTS idx_readings_sensor_time ON sensor_readings(sensor_id,reading_time);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        """)
        # Backward-compatible schema migration for databases created by earlier builds.
        sensor_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(sensors)")}
        if "battery" not in sensor_columns:
            self.connection.execute("ALTER TABLE sensors ADD COLUMN battery REAL NOT NULL DEFAULT 100")
        if "last_fault" not in sensor_columns:
            self.connection.execute("ALTER TABLE sensors ADD COLUMN last_fault TEXT")
        self.connection.commit()
    def seed_demo_data(self):
        demos=[("Демо-агроном","agronomist@example.com","Агроном"),("Демо-агроскаут","scout@example.com","Агроскаут"),("Демо-инженер","engineer@example.com","Инженер-механизатор"),("Демо-аналитик","analyst@example.com","Аналитик"),("Демо-ведомство","agency@example.com","Государственное / экологическое ведомство")]
        # Keep demo credentials deterministic even when an older database already exists.
        # INSERT OR IGNORE alone left stale password hashes in databases created by earlier builds.
        for name,email,role in demos:
            existing = self.query("SELECT id FROM users WHERE lower(email)=lower(?)", (email,))
            if existing:
                self.execute("UPDATE users SET name=?, password_hash=?, role=? WHERE lower(email)=lower(?)",
                             (name, password_hash("demo123"), role, email))
            else:
                self.execute("INSERT INTO users VALUES(?,?,?,?,?)",(str(uuid.uuid4()),name,email,password_hash("demo123"),role))
        if not self.query("SELECT id FROM fields LIMIT 1"):
            self.execute("INSERT INTO fields VALUES(?,?)",("FIELD-01","55.7512, 37.6184")); self.execute("INSERT INTO fields VALUES(?,?)",("FIELD-02","55.7612, 37.6284"))
            self.execute("INSERT INTO sensors(id,type,coordinates,status,field_id,battery) VALUES(?,?,?,?,?,?)",("S-001","Влажность почвы","55.7512, 37.6184","Работает","FIELD-01",82)); self.execute("INSERT INTO sensors(id,type,coordinates,status,field_id,battery) VALUES(?,?,?,?,?,?)",("S-002","Температура","55.7612, 37.6284","Требует проверки","FIELD-02",16))
            now=datetime.now()
            for sid,typ,val in [("S-001","Влажность почвы",62),("S-002","Температура",31.2)]: self.execute("INSERT INTO sensor_readings VALUES(?,?,?,?,?)",(str(uuid.uuid4()),typ,val,now.isoformat(timespec="minutes"),sid))
            self.execute("INSERT INTO problem_areas VALUES(?,?,?,?,?)",("P-001","Низкая влажность","55.7512, 37.6184","Открыта","FIELD-01")); self.execute("INSERT INTO problem_areas VALUES(?,?,?,?,?)",("P-002","Повышенная температура","55.7612, 37.6284","На проверке","FIELD-02"))
            agr=self.query("SELECT id FROM users WHERE role=? LIMIT 1",("Агроном",))[0]["id"]
            self.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",("T-001","Полив","Новое",(now+timedelta(days=1)).date().isoformat(),agr,"P-001")); self.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",("T-002","Проверка участка","В работе",(now+timedelta(days=2)).date().isoformat(),agr,"P-002"))
        if not self.query("SELECT id FROM machinery LIMIT 1"):
            self.execute("INSERT INTO machinery VALUES(?,?,?,?,?,?)",("TR-001","Трактор №1","Трактор","55.7512, 37.6184","На линии",76))
            self.execute("INSERT INTO machinery VALUES(?,?,?,?,?,?)",("TR-002","Комбайн №2","Комбайн","55.7612, 37.6284","На обслуживании",18))
        self._ensure_demo_reading_history()
    def _ensure_demo_reading_history(self):
        """Provide a small dated history so the agronomist's trend chart is useful on first run."""
        sensors = self.query("SELECT id,type FROM sensors ORDER BY id")
        now = datetime.now().replace(second=0, microsecond=0)
        for sensor in sensors:
            count = self.query("SELECT COUNT(*) AS n FROM sensor_readings WHERE sensor_id=?", (sensor['id'],))[0]['n']
            if count >= 7:
                continue
            for days_ago in range(13, -1, -1):
                stamp = (now - timedelta(days=days_ago)).isoformat(timespec="minutes")
                exists = self.query("SELECT id FROM sensor_readings WHERE sensor_id=? AND reading_time=?", (sensor['id'], stamp))
                if exists:
                    continue
                wave = math.sin((13-days_ago) * 0.72)
                if "влаж" in sensor['type'].lower():
                    value = round(48 + (13-days_ago)*1.05 + wave*3.2, 1)
                elif "температур" in sensor['type'].lower():
                    value = round(27.5 + wave*2.4 + (13-days_ago)*0.12, 1)
                else:
                    value = round(50 + wave*4, 1)
                self.execute("INSERT INTO sensor_readings VALUES(?,?,?,?,?)",
                             (str(uuid.uuid4()), sensor['type'], value, stamp, sensor['id']))
    def close(self): self.connection.close()
