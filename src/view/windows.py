from PyQt6.QtCore import Qt, QDate, QPointF
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QPen, QColor
from PyQt6.QtWidgets import (QWidget,QMainWindow,QStackedWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QFormLayout,QLabel,QLineEdit,QPushButton,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QFrame,QTextEdit,QDateEdit,QMessageBox,QFileDialog,QGroupBox,QListWidget,QListWidgetItem,QSplitter,QAbstractItemView)
from datetime import datetime
import csv
from pathlib import Path
from src.infrastructure.database import ROLES
from src.view.interfaces import ICropMonitoringView,IEquipmentMonitoringView,IInspectionView,ITaskView,IReportView,BaseView
from src.controllers.controllers import CropMonitoringController, AnalysisController, EquipmentMonitoringController, InspectionController, TaskController, ReportController
from src.model.repositories import SensorReadingRepository, TaskRepository, ReportRepository
from src.view.state_navigation import TRANSITIONS, LOGOUT_STATES

GREEN="#27833b"; GREEN_DARK="#176b2b"; BG="#f2f3f5"; BORDER="#d8dadd"; TEXT="#30343b"; MUTED="#72777f"; RED="#c94343"; ORANGE="#e78b22"
APP_QSS=f"""
QWidget {{ color:{TEXT}; font-family:'Segoe UI',Arial; font-size:10pt; }}
QMainWindow,QWidget#root {{ background:{BG}; }}
QFrame[card='true'], QGroupBox {{ background:white; border:1px solid {BORDER}; border-radius:5px; }}
QGroupBox {{ margin-top:12px; padding:12px 8px 8px 8px; font-weight:600; }}
QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}
QLineEdit,QComboBox,QDateEdit,QTextEdit {{ background:white; border:1px solid #cfd2d6; border-radius:3px; padding:6px 8px; min-height:22px; selection-background-color:{GREEN}; }}
QPushButton {{ background:#e7e9ec; color:#252a31; border:1px solid #b9bec5; border-radius:4px; padding:7px 13px; min-height:18px; font-weight:500; }}
QPushButton:hover {{ background:#d9e2da; color:#17251a; border-color:#87988a; }}
QPushButton:pressed {{ background:#cbd5cd; }}
QPushButton[primary='true'] {{ background:{GREEN}; color:#ffffff; border:1px solid {GREEN_DARK}; font-weight:700; }}
QPushButton[primary='true']:hover {{ background:{GREEN_DARK}; color:#ffffff; }}
QPushButton[primary='true']:pressed {{ background:#105320; }}
QPushButton[danger='true'] {{ background:{RED}; color:#ffffff; border-color:#a72d2d; font-weight:600; }}
QListWidget {{ background:#ffffff; color:{TEXT}; border:1px solid {BORDER}; border-radius:3px; padding:4px; selection-background-color:#e3f1e5; selection-color:{TEXT}; }}
QListWidget::item {{ background:#ffffff; color:{TEXT}; padding:7px 6px; border:0; }}
QListWidget::item:hover {{ background:#f3f7f3; color:{TEXT}; }}
QListWidget::item:selected {{ background:#e3f1e5; color:{TEXT}; border-left:3px solid {GREEN}; }}
QTableWidget {{ background:white; border:1px solid {BORDER}; gridline-color:#e4e5e7; selection-background-color:#e3f1e5; selection-color:{TEXT}; }}
QHeaderView::section {{ background:#f1f2f3; border:0; border-right:1px solid {BORDER}; border-bottom:1px solid {BORDER}; padding:7px; font-weight:600; }}
QLabel#pageTitle {{ color:{GREEN_DARK}; font-size:15pt; font-weight:700; }}
QLabel#sectionTitle {{ font-weight:600; font-size:10.5pt; }}
QLabel#muted {{ color:{MUTED}; }}
"""

def label(text, style=None):
    w=QLabel(text)
    if style: w.setObjectName(style)
    return w

def btn(text, callback=None, primary=False, danger=False):
    b=QPushButton(text)
    if primary:
        b.setProperty('primary','true')
        b.setStyleSheet(f"background:{GREEN};color:white;border:1px solid {GREEN_DARK};border-radius:4px;padding:7px 13px;font-weight:700; min-height:18px;")
    elif danger:
        b.setProperty('danger','true')
        b.setStyleSheet(f"background:{RED};color:white;border:1px solid #a72d2d;border-radius:4px;padding:7px 13px;font-weight:600; min-height:18px;")
    else:
        b.setStyleSheet("background:#e7e9ec;color:#252a31;border:1px solid #b9bec5;border-radius:4px;padding:7px 13px;min-height:18px;")
    if callback: b.clicked.connect(callback)
    return b

def card(title=None):
    f=QFrame(); f.setProperty('card','true'); l=QVBoxLayout(f); l.setContentsMargins(10,9,10,9); l.setSpacing(7)
    if title: l.addWidget(label(title,'sectionTitle'))
    return f,l

def table(headers, rows=(), widths=None):
    t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers); t.setAlternatingRowColors(False)
    t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); t.setMinimumHeight(150)
    if widths:
        for i,w in enumerate(widths): t.setColumnWidth(i,w)
    for row in rows: add_row(t,row)
    return t

def add_row(t,row):
    n=t.rowCount(); t.insertRow(n)
    for c,val in enumerate(row): t.setItem(n,c,QTableWidgetItem(str(val if val is not None else "")))

def selected_id(t,col=0):
    r=t.currentRow(); it=t.item(r,col) if r>=0 else None
    return it.text() if it else None


class MetricTrendChart(QWidget):
    """Lightweight native Qt line chart; no extra plotting dependency is required."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values=[]; self.metric="Показатель"; self.setMinimumHeight(185); self.setMinimumWidth(300)
        self.setStyleSheet("background:#ffffff;")
    def set_data(self, readings, metric):
        rows=[r for r in readings if r.get('type')==metric]
        rows.sort(key=lambda r:r.get('reading_time',''))
        self.values=rows; self.metric=metric or "Показатель"; self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=self.rect(); p.fillRect(rect,QColor("#ffffff"))
        p.setPen(QColor("#333b43")); p.drawText(12,20,f"Динамика: {self.metric}")
        if not self.values:
            p.setPen(QColor("#777f87")); p.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Для выбранного показателя пока нет истории")
            p.end(); return
        left,right,top,bottom=48,16,34,34
        x0,y0=left,top; x1,y1=max(left+20,rect.width()-right),max(top+20,rect.height()-bottom)
        vals=[float(r['value']) for r in self.values]; lo=min(vals); hi=max(vals)
        pad=max((hi-lo)*0.15, 1.0); lo-=pad; hi+=pad
        p.setPen(QPen(QColor("#e6e9ec"),1))
        for i in range(5):
            y=y0+(y1-y0)*i/4; p.drawLine(x0,int(y),x1,int(y))
            tick=hi-(hi-lo)*i/4; p.setPen(QColor("#68727c")); p.drawText(4,int(y)+4,f"{tick:.1f}"); p.setPen(QPen(QColor("#e6e9ec"),1))
        path=QPainterPath()
        points=[]
        n=len(vals)
        for i,value in enumerate(vals):
            x=x0+(x1-x0)*(i/(n-1) if n>1 else 0.5)
            y=y1-(value-lo)/(hi-lo)*(y1-y0)
            points.append(QPointF(x,y))
        if points:
            path.moveTo(points[0])
            for pt in points[1:]: path.lineTo(pt)
            p.setPen(QPen(QColor("#27833b"),2.5)); p.drawPath(path)
            p.setBrush(QColor("#176b2b")); p.setPen(Qt.PenStyle.NoPen)
            for pt in points: p.drawEllipse(pt,3.2,3.2)
        p.setPen(QColor("#68727c"))
        first=self.values[0].get('reading_time','')[:10]; last=self.values[-1].get('reading_time','')[:10]
        p.drawText(x0,y1+22,first); p.drawText(max(x0,x1-75),y1+22,last)
        p.end()

class SimpleBarChart(QWidget):
    """Small native Qt chart used by the report dashboard; no new package needed."""
    def __init__(self,title="",parent=None):
        super().__init__(parent); self.title=title; self.labels=[]; self.values=[]; self.setMinimumHeight(175); self.setMinimumWidth(260)
        self.setStyleSheet("background:#ededed;border:1px dashed #bfc3c7")
    def set_data(self,labels,values,title=None):
        self.labels=list(labels); self.values=[float(v) for v in values]
        if title is not None:self.title=title
        self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); rect=self.rect(); p.fillRect(rect,QColor("#ededed"))
        p.setPen(QColor("#38424b")); p.drawText(10,20,self.title)
        if not self.values:
            p.setPen(QColor("#68727c")); p.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Нет данных для выбранного периода"); p.end(); return
        left,right,top,bottom=38,12,34,40; w=max(10,rect.width()-left-right); h=max(10,rect.height()-top-bottom)
        maximum=max(max(self.values),0.01); n=len(self.values); slot=w/n; barw=max(8,slot*0.55)
        p.setPen(QPen(QColor("#cfd3d7"),1)); p.drawLine(left,top,left,top+h); p.drawLine(left,top+h,left+w,top+h)
        for i,(name,val) in enumerate(zip(self.labels,self.values)):
            bh=h*val/maximum; x=left+i*slot+(slot-barw)/2; y=top+h-bh
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#27833b")); p.drawRoundedRect(int(x),int(y),int(barw),max(2,int(bh)),3,3)
            p.setPen(QColor("#38424b")); p.drawText(int(x-4),max(top+12,int(y)-4),int(barw+8),16,Qt.AlignmentFlag.AlignCenter,f"{val:.2f}" if val<1 else f"{val:g}")
            text=name if len(name)<=12 else name[:11]+"…"
            p.drawText(int(left+i*slot),top+h+5,int(slot),30,Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop,text)
        p.end()

class LoginWindow(QWidget):
    def __init__(self,userRepo,on_login,on_register):
        super().__init__(); self.userRepo=userRepo; self.on_login=on_login
        self.setStyleSheet(f'background:{BG};'); root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addStretch()
        box=QFrame(); box.setFixedWidth(420); box.setStyleSheet("QFrame{background:white;border:1px solid #e0e1e3;border-radius:7px;}")
        v=QVBoxLayout(box); v.setContentsMargins(28,26,28,22); v.setSpacing(12)
        title=label("Система мониторинга\nсостояния растений"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setStyleSheet(f"color:{GREEN_DARK};font-size:20pt;font-weight:700;border:0")
        sub=label("Вход в десктопное приложение"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter); sub.setStyleSheet("color:#777;border:0")
        self.email=QLineEdit(); self.email.setPlaceholderText("Email / логин")
        self.password=QLineEdit(); self.password.setPlaceholderText("Пароль"); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role=QComboBox(); self.role.addItems(ROLES)
        login=btn("Войти",self.login,True); login.setMinimumHeight(38)
        links=QHBoxLayout(); reg=QPushButton("Регистрация"); reg.setFlat(True); reg.setStyleSheet("color:#2877b8;border:0;background:transparent;text-align:left")
        forgot=QPushButton("Забыли пароль?"); forgot.setFlat(True); forgot.setStyleSheet("color:#2877b8;border:0;background:transparent")
        reg.clicked.connect(on_register); forgot.clicked.connect(lambda: QMessageBox.information(self,"Восстановление пароля","Обратитесь к администратору системы для сброса пароля."))
        links.addWidget(forgot); links.addStretch(); links.addWidget(reg)
        for w in (title,sub,self.email,self.password,label("Роль"),self.role,login): v.addWidget(w)
        v.addLayout(links)
        demo=label("Демо-доступ: выберите роль, email можно оставить пустым.\nПароль: demo123"); demo.setAlignment(Qt.AlignmentFlag.AlignCenter); demo.setStyleSheet("color:#888;font-size:8pt;border:0")
        v.addWidget(demo)
        root.addWidget(box,0,Qt.AlignmentFlag.AlignHCenter); root.addStretch()
    def login(self):
        email=self.email.text().strip()
        password=self.password.text()
        role=self.role.currentText()
        if not password:
            QMessageBox.warning(self,"Не указан пароль","Введите пароль. Для демонстрационных учётных записей пароль: demo123.")
            return
        try:
            # Пустой email разрешён только для демонстрационного входа выбранной роли.
            if not email:
                demo_by_role = {
                    "Агроном":"agronomist@example.com", "Агроскаут":"scout@example.com",
                    "Инженер-механизатор":"engineer@example.com", "Аналитик":"analyst@example.com",
                    "Государственное / экологическое ведомство":"agency@example.com",
                }
                email = demo_by_role[role]
            user=self.userRepo.authenticateUser(email,password,role)
        except Exception as e:
            QMessageBox.warning(self,"Ошибка входа",f"Не удалось выполнить вход: {e}"); return
        if not user:
            QMessageBox.warning(self,"Вход не выполнен","Проверьте email, пароль и выбранную роль. Для демонстрационных учётных записей пароль: demo123.")
            return
        self.on_login(user)

class RegistrationWindow(QWidget):
    def __init__(self,userRepo,on_back):
        super().__init__(); self.userRepo=userRepo; self.on_back=on_back
        self.setStyleSheet(f'background:{BG};'); root=QVBoxLayout(self); root.addStretch(); box=QFrame(); box.setFixedWidth(480); box.setStyleSheet("QFrame{background:white;border:1px solid #ddd;border-radius:6px}")
        v=QVBoxLayout(box); v.setContentsMargins(28,24,28,24)
        h=label("Регистрация нового пользователя"); h.setAlignment(Qt.AlignmentFlag.AlignCenter); h.setStyleSheet(f"color:{GREEN_DARK};font-size:17pt;font-weight:700;border:0")
        s=label("Заполните данные учётной записи и выберите роль"); s.setAlignment(Qt.AlignmentFlag.AlignCenter); s.setStyleSheet("color:#777;border:0")
        v.addWidget(h); v.addWidget(s)
        self.name=QLineEdit(); self.name.setPlaceholderText("ФИО"); self.email=QLineEdit(); self.email.setPlaceholderText("Email")
        self.password=QLineEdit(); self.password.setPlaceholderText("Пароль"); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm=QLineEdit(); self.confirm.setPlaceholderText("Повторите пароль"); self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.role=QComboBox(); self.role.addItems(ROLES)
        for title,w in [("ФИО",self.name),("Email",self.email),("Пароль",self.password),("Повтор пароля",self.confirm),("Роль",self.role)]: v.addWidget(label(title)); v.addWidget(w)
        row=QHBoxLayout(); row.addWidget(btn("Зарегистрироваться",self.register,True)); row.addWidget(btn("Уже есть аккаунт? Войти",on_back)); v.addLayout(row)
        root.addWidget(box,0,Qt.AlignmentFlag.AlignHCenter); root.addStretch()
    def register(self):
        name,email,pw=self.name.text().strip(),self.email.text().strip(),self.password.text()
        if not name or not email or len(pw)<6 or pw!=self.confirm.text(): QMessageBox.warning(self,"Проверка данных","Заполните все поля. Пароль — не менее 6 символов, подтверждение должно совпадать."); return
        try:
            from src.model.entities import User, Agronomist, CropScout, Engineer, Analyst, GovernmentAgency
            role_types = {"Агроном": Agronomist, "Агроскаут": CropScout,
                          "Инженер-механизатор": Engineer, "Аналитик": Analyst,
                          "Государственное / экологическое ведомство": GovernmentAgency}
            user_type = role_types.get(self.role.currentText(), User)
            user = user_type(id=__import__("uuid").uuid4().hex, name=name, email=email, password=pw)
            # UserRepository.createUser(user) is the exact UML signature.
            self.userRepo.createUser(user)
        except Exception as e: QMessageBox.warning(self,"Регистрация",f"Не удалось зарегистрировать пользователя: {e}"); return
        QMessageBox.information(self,"Регистрация","Учётная запись создана. Теперь войдите в систему."); self.on_back()

class MainShell(QMainWindow):
    # The UI state diagram is implemented as an explicit transition graph.
    # Role-specific page sets are kept separate so an engineer never receives
    # the agronomist dashboard merely because it exists in the global state graph.
    ROLE_PAGES={
        "Агроном":["W1 — Мониторинг полей","W2 — Карточка проблемной зоны","W3 — Задания","W6 — Отчёты и аналитика"],
        "Агроскаут":["W4 — Полевое обследование","W2 — Карточка проблемной зоны"],
        "Инженер-механизатор":["W5 — Контроль оборудования"],
        "Аналитик":["W6 — Отчёты и аналитика"],
        "Государственное / экологическое ведомство":["W7 — Контроль землепользования"]
    }
    def __init__(self,container,user,on_logout):
        super().__init__(); self.c=container; self.user=user; self.on_logout=on_logout; self.current_page=""
        self.setWindowTitle("Система мониторинга состояния растений"); self.resize(1240,790); self.setMinimumSize(1050,680)
        central=QWidget(); central.setObjectName('root'); self.setCentralWidget(central); root=QVBoxLayout(central); root.setContentsMargins(10,8,10,10); root.setSpacing(8)
        top=QHBoxLayout(); self.brand=label("🌱  Система мониторинга растений"); self.brand.setStyleSheet(f"font-weight:700;color:{GREEN_DARK};font-size:15pt")
        self.search=QLineEdit(); self.search.setPlaceholderText("Поиск по полям / зонам…"); self.search.setMaximumWidth(250)
        self.search.textChanged.connect(self.apply_search)
        top.addWidget(self.brand); top.addStretch(); top.addWidget(self.search); top.addWidget(label(user['name']+"  •  "+user['role']))
        self.logout_button=btn("Выход",on_logout); top.addWidget(self.logout_button); root.addLayout(top)
        self.stack=QStackedWidget(); root.addWidget(self.stack,1)
        self.pages={}
        for name in self.ROLE_PAGES[user['role']]:
            page=self.make_page(name); self.pages[name]=page; self.stack.addWidget(page)
        self.show_page(self.ROLE_PAGES[user['role']][0])
    def show_page(self,name):
        if name not in self.pages: return
        self.current_page=name; self.stack.setCurrentWidget(self.pages[name])
        state=name.split(" — ",1)[0]
        self.logout_button.setVisible(state in LOGOUT_STATES)
        page=self.pages[name]
        self.brand.setText(page.page_title)
        if hasattr(page,"on_show"): page.on_show()
        self.apply_search(self.search.text())

    def apply_search(self,text):
        page=self.pages.get(self.current_page)
        if page and hasattr(page,"apply_search"):
            page.apply_search(text.strip().lower())
    def make_page(self,name):
        if name.startswith("W1"): return AgronomistMapPage(self)
        if name.startswith("W2"): return ProblemAreaPage(self)
        if name.startswith("W3"): return TasksPage(self)
        if name.startswith("W4"): return InspectionPage(self)
        if name.startswith("W5"): return EquipmentPage(self)
        if name.startswith("W6"): return ReportsPage(self)
        return GovernmentPage(self)
    def navigate(self,prefix):
        target=prefix.split(" — ",1)[0]
        current=self.current_page.split(" — ",1)[0]
        if target=="W0":
            if target in TRANSITIONS.get(current,set()): self.on_logout()
            return
        if target not in TRANSITIONS.get(current,set()):
            QMessageBox.information(self,"Переход недоступен",f"Переход {current} → {target} не предусмотрен диаграммой состояний.")
            return
        for name in self.pages:
            if name.startswith(target):
                self.show_page(name)
                return
        QMessageBox.information(self,"Окно недоступно",f"Окно {target} не входит в набор окон роли «{self.user['role']}».")

class Page(QWidget):
    def render(self,data): self.update(data)
    def update(self,data): return None
    def __init__(self,shell,title):
        super().__init__(); self.s=shell; self.page_title=title; root=QVBoxLayout(self); root.setContentsMargins(4,4,4,4); root.setSpacing(8)
        head=QHBoxLayout(); self.header=head; root.addLayout(head); self.body=QVBoxLayout(); self.body.setSpacing(8); root.addLayout(self.body,1)
    def refresh(self): pass

class AgronomistMapPage(Page,ICropMonitoringView):
    """W1. Agronomist dashboard follows the supplied mock-up."""
    def __init__(self,s):
        super().__init__(s,"🌱  Мониторинг полей")
        self.header.addWidget(btn("Обновить данные",self.refresh))
        grid=QGridLayout(); grid.setColumnStretch(0,2); grid.setColumnStretch(1,5); grid.setColumnStretch(2,2); grid.setRowStretch(0,1)
        self.body.addLayout(grid,1)
        f,l=card("Поля")
        self.fields=QListWidget(); self.fields.currentTextChanged.connect(self.select_field)
        l.addWidget(self.fields); grid.addWidget(f,0,0)

        f,l=card("Карта состояния")
        self.map=label("КАРТА ПОЛЕЙ\n\nЦветовая индикация состояния посевов\nВыберите поле слева")
        self.map.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map.setStyleSheet("background:#ededed;color:#68727c;border:1px dashed #bfc3c7;min-height:260px")
        l.addWidget(self.map,1)
        legend=QHBoxLayout()
        for color,text in [("#27833b","норма"),("#f0b323","внимание"),("#e77a16","риск"),("#c94343","критично")]:
            swatch=QLabel("  "); swatch.setStyleSheet(f"background:{color};max-width:12px;max-height:12px")
            legend.addWidget(swatch); legend.addWidget(label(text,'muted'))
        legend.addStretch(); l.addLayout(legend); grid.addWidget(f,0,1)

        right=QVBoxLayout(); right.setSpacing(8)
        f,l=card("Показатели датчиков")
        self.metrics_layout=QVBoxLayout(); self.metrics_layout.setSpacing(6); l.addLayout(self.metrics_layout)
        right.addWidget(f,1)
        f,l=card("Проблемные зоны")
        self.zone_list=QListWidget(); self.zone_list.itemClicked.connect(self.open_zone_item)
        l.addWidget(self.zone_list,1); right.addWidget(f,2)
        grid.addLayout(right,0,2)

        row=QHBoxLayout()
        row.addWidget(btn("Зафиксировать отклонение",lambda:s.navigate("W2"),False))
        row.addWidget(btn("Перейти к заданию через карточку зоны",lambda:s.navigate("W2"),True))
        row.addWidget(btn("Открыть карточку зоны",lambda:s.navigate("W2")))
        row.addStretch()
        row.addWidget(btn("Отчёты и аналитика",lambda:s.navigate("W6")))
        self.body.addLayout(row)
        self.refresh()

    def showFieldMap(self,fields,zones):
        self.map.setText(f"КАРТА ПОЛЕЙ\n\nПолей: {len(fields)}\nПроблемных зон: {len(zones)}")
    def highlightProblemAreas(self,zones):
        self.map.setText("Проблемные зоны:\n"+", ".join(z['id'] for z in zones))
    def showReadings(self,readings):
        self._render_metrics(readings)

    def _render_metrics(self,readings):
        # Remove both widgets and nested layouts. The previous implementation
        # removed only widgets; every old QGridLayout remained attached and
        # accumulated when the user switched fields, causing labels to overlap.
        while self.metrics_layout.count():
            item = self.metrics_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._dispose_layout(child_layout)
                child_layout.deleteLater()

        latest={}
        for r in readings:
            latest.setdefault(r['type'],r)
        if not latest:
            empty=label("Нет показаний датчиков",'muted')
            empty.setWordWrap(True)
            self.metrics_layout.addWidget(empty)
            return

        for typ,r in latest.items():
            line=QFrame()
            line.setObjectName("metricRow")
            line.setStyleSheet("QFrame#metricRow { background:#ffffff; border:0; }")
            row=QHBoxLayout(line)
            row.setContentsMargins(0,2,0,2)
            row.setSpacing(8)
            name=label(str(typ))
            name.setWordWrap(True)
            name.setMinimumWidth(0)
            value=label(str(r['value']))
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setMinimumWidth(82)
            value.setMinimumHeight(54)
            value.setStyleSheet("background:#ededed;border:1px dashed #bfc3c7;padding:6px;color:#53606c")
            row.addWidget(name, 3)
            row.addWidget(value, 2)
            self.metrics_layout.addWidget(line)

    @staticmethod
    def _dispose_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            nested = item.layout()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif nested is not None:
                AgronomistMapPage._dispose_layout(nested)
                nested.deleteLater()

    def on_show(self):
        self.refresh()

    def apply_search(self,query):
        for widget in (self.fields,self.zone_list):
            for index in range(widget.count()):
                item=widget.item(index)
                item.setHidden(bool(query) and query not in item.text().lower())

    def refresh(self):
        fields=self.s.c.resolve(CropMonitoringController).getFieldsOverview()
        current=self.fields.currentItem().data(Qt.ItemDataRole.UserRole) if self.fields.currentItem() else None
        self.fields.blockSignals(True); self.fields.clear()
        display_names={"FIELD-01":"Поле №1 «Северное»", "FIELD-02":"Поле №2 «Луговое»"}
        for index, f in enumerate(fields, start=1):
            item=QListWidgetItem(display_names.get(f['id'], f"Поле №{index} «{f['id']}»"))
            item.setData(Qt.ItemDataRole.UserRole, f['id'])
            self.fields.addItem(item)
        if current:
            for i in range(self.fields.count()):
                if self.fields.item(i).data(Qt.ItemDataRole.UserRole)==current:
                    self.fields.setCurrentRow(i); break
        if self.fields.currentRow()<0 and fields: self.fields.setCurrentRow(0)
        self.fields.blockSignals(False)
        self.select_field(self.fields.currentItem().text() if self.fields.currentItem() else "")

    def select_field(self,_display_text):
        item=self.fields.currentItem()
        fid=item.data(Qt.ItemDataRole.UserRole) if item else None
        if not fid:return
        all_fields=self.s.c.resolve(CropMonitoringController).getFieldsOverview()
        field=next((x for x in all_fields if x['id']==fid),None)
        rows=self.s.c.resolve(CropMonitoringController).getReadingsByField(fid)
        self._render_metrics(rows)
        zones=[z for z in self.s.c.resolve(CropMonitoringController).getProblemAreas() if z['field_id']==fid]
        self.map.setText(f"КАРТА ПОЛЕЙ\n\n{fid}\n\nКоординаты: {field['coordinates'] if field else '—'}\n\nПроблемных зон: {len(zones)}\n\n(схематическое представление участка)")
        self.zone_list.clear()
        inspections=self.s.c.resolve(InspectionController).getInspectionsByField(fid)
        for z in zones:
            recent=next((i for i in inspections if i.get('problem_area_id')==z['id']),None)
            suffix="  •  получен результат агроскаута" if recent else ""
            field_number = "1" if z['field_id']=="FIELD-01" else ("2" if z['field_id']=="FIELD-02" else z['field_id'])
            item=QListWidgetItem(f"⚠  Зона {z['id']}: {z['problem_type']} (Поле {field_number}){suffix}")
            item.setData(Qt.ItemDataRole.UserRole,z['id']); self.zone_list.addItem(item)

    def open_zone_item(self,item):
        self.s.selected_zone_id=item.data(Qt.ItemDataRole.UserRole); self.s.navigate("W2")

class ProblemAreaPage(Page,ICropMonitoringView):
    """W2. Zone card with sensor trend and the scout's submitted inspection result."""
    def __init__(self,s):
        super().__init__(s,"Проблемная зона")
        top=QHBoxLayout(); self.zone_title=label("Проблемная зона",'sectionTitle'); top.addWidget(self.zone_title); top.addStretch()
        top.addWidget(label("Статус:")); self.status=QComboBox(); self.status.addItems(["Выявлена","Открыта","На проверке","Подтверждена","Устранена"]); top.addWidget(self.status)
        if s.user['role']=="Агроскаут":
            self.back_button=btn("Назад к полевому обследованию",lambda:s.navigate("W4"))
            self.back_button.setVisible(True)
        else:
            self.back_button=btn("Назад",lambda:s.navigate("W1"))
            self.back_button.setVisible(s.user['role']=="Агроном")
        top.addWidget(self.back_button); self.body.addLayout(top)
        self.zones=s.c.resolve(CropMonitoringController).getProblemAreas()
        self.current_zone_id=getattr(s,'selected_zone_id',None) or (self.zones[0]['id'] if self.zones else None)

        grid=QGridLayout(); grid.setColumnStretch(0,1); grid.setColumnStretch(1,1); grid.setColumnStretch(2,1); self.body.addLayout(grid)
        f,l=card("Фрагмент карты зоны")
        self.coords=label("Метка зоны + контур поля"); self.coords.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.coords.setStyleSheet("background:#ededed;color:#68727c;border:1px dashed #bfc3c7;min-height:150px")
        l.addWidget(self.coords,1); grid.addWidget(f,0,0)

        f,l=card("Динамика показателей")
        metric_row=QHBoxLayout(); metric_row.addWidget(label("Показатель:")); self.metric=QComboBox(); self.metric.currentTextChanged.connect(self.update_chart); metric_row.addWidget(self.metric,1); l.addLayout(metric_row)
        self.trend=MetricTrendChart(); self.trend.setMinimumHeight(150); l.addWidget(self.trend,1); grid.addWidget(f,0,1)

        f,l=card("Индекс состояния растения")
        self.health=label("Health Index = —\n(порог 0.60)"); self.health.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.health.setStyleSheet("background:#ededed;color:#53606c;border:1px dashed #bfc3c7;min-height:150px;font-size:12pt")
        l.addWidget(self.health,1); grid.addWidget(f,0,2)

        self.scout_notice=QLabel(); self.scout_notice.setWordWrap(True)
        self.scout_notice.setStyleSheet("background:#fff7e6;border:1px solid #edc46b;border-radius:4px;padding:7px;color:#684b12")
        self.body.addWidget(self.scout_notice)

        f,l=card("Последние показания датчиков")
        self.readings=table(["Тип","Значение","Время замера","Датчик","Статус"]); l.addWidget(self.readings); self.body.addWidget(f,1)
        row=QHBoxLayout()
        self.confirm_button=btn("Подтвердить обследование",self.confirm,True)
        self.task_button=btn("Назначить задание",lambda:s.navigate("W3"),False)
        self.comment_button=btn("Комментарий агронома",self.comment)
        self.analytics_button=btn("Отчёты и аналитика",lambda:s.navigate("W6"))
        for w in (self.confirm_button,self.task_button,self.comment_button,self.analytics_button): row.addWidget(w)
        row.addStretch(); self.body.addLayout(row)
        scout_mode=s.user['role']=="Агроскаут"
        for w in (self.confirm_button,self.task_button,self.comment_button,self.analytics_button): w.setVisible(not scout_mode)
        self.status.setEnabled(not scout_mode)
        self.load_zone()

    def on_show(self):
        self.zones=self.s.c.resolve(CropMonitoringController).getProblemAreas()
        selected=getattr(self.s,'selected_zone_id',None)
        if selected and any(z['id']==selected for z in self.zones):
            self.current_zone_id=selected
        elif self.zones and not any(z['id']==self.current_zone_id for z in self.zones):
            self.current_zone_id=self.zones[0]['id']
        self.load_zone()

    def load_zone(self,*_):
        if not self.zones:return
        z=next((x for x in self.zones if x['id']==self.current_zone_id),self.zones[0])
        self.current_zone_id=z['id']; self.s.selected_zone_id=z['id']; self.zone_title.setText(f"Проблемная зона {z['id']}")
        self.status.setCurrentText(z['status'] if z['status'] in [self.status.itemText(i) for i in range(self.status.count())] else "Выявлена")
        self.coords.setText(f"Поле: {z['field_id']}\nКоординаты: {z['coordinates']}\nМетка зоны + контур поля")
        rows=self.s.c.resolve(CropMonitoringController).getReadingsByField(z['field_id'])
        self.readings.setRowCount(0)
        for r in rows:add_row(self.readings,[r['type'],r['value'],r['reading_time'],r['sensor_id'],"Получено"])
        metric_names=sorted({r['type'] for r in rows})
        current=self.metric.currentText(); self.metric.blockSignals(True); self.metric.clear(); self.metric.addItems(metric_names)
        if current in metric_names:self.metric.setCurrentText(current)
        self.metric.blockSignals(False); self.update_chart()
        index=self.s.c.resolve(AnalysisController).computeHealthIndex(z['field_id'])/100.0
        self.health.setText(f"Health Index = {index:.2f}\n(порог 0.60)")
        inspections=self.s.c.resolve(InspectionController).getInspectionsByField(z['field_id'])
        inspection=next((i for i in inspections if i.get('problem_area_id')==z['id']),None)
        if inspection:
            self.scout_notice.setText(f"Результат обследования агроскаута от {inspection['timestamp']}: {inspection['description']}\nФотоотчёт: {inspection.get('photo_report') or 'не приложен'}. Результат сохранён в системе и доступен агроному.")
            self.scout_notice.show()
        else:
            self.scout_notice.setText("Результат агроскаута по этой зоне ещё не поступал. После отправки обследования он появится здесь.")
            self.scout_notice.show()

    def update_chart(self,*_):
        if not self.zones or not self.current_zone_id:return
        z=next((x for x in self.zones if x['id']==self.current_zone_id),self.zones[0])
        rows=self.s.c.resolve(CropMonitoringController).getReadingsByField(z['field_id'])
        self.trend.set_data(rows,self.metric.currentText())

    def confirm(self):
        if not self.zones or not self.current_zone_id:return
        z=next((x for x in self.zones if x['id']==self.current_zone_id),self.zones[0])
        self.s.c.resolve(CropMonitoringController).updateProblemArea(z['id'],self.status.currentText())
        self.zones=self.s.c.resolve(CropMonitoringController).getProblemAreas()
        QMessageBox.information(self,"Сохранено","Статус проблемной зоны обновлён.")
        self.load_zone()

    def comment(self):
        from PyQt6.QtWidgets import QInputDialog
        note,ok=QInputDialog.getMultiLineText(self,"Комментарий агронома","Комментарий к результату обследования:")
        if not ok or not note.strip():return
        z=next((x for x in self.zones if x['id']==self.current_zone_id),None)
        if not z:return
        inspections=self.s.c.resolve(InspectionController).getInspectionsByField(z['field_id'])
        inspection=next((i for i in inspections if i.get('problem_area_id')==z['id']),None)
        if not inspection:
            QMessageBox.information(self,"Комментарий","Сначала агроскаут должен отправить результат обследования. Комментарий будет добавлен к его записи.")
            return
        inspection['description']=(inspection.get('description','')+"\nКомментарий агронома: "+note.strip()).strip()
        self.s.c.resolve(InspectionController).updateInspection(inspection)
        self.load_zone()
        QMessageBox.information(self,"Комментарий","Комментарий сохранён в описании существующего обследования.")

class TasksPage(Page,ITaskView):
    def __init__(self,s):
        super().__init__(s,"🌱  Задания")
        row=QHBoxLayout(); self.status=QComboBox(); self.status.addItems(["Все","Новое","В работе","Выполнено"]); self.status.currentTextChanged.connect(self.refresh)
        row.addWidget(label("Статус:")); row.addWidget(self.status); row.addStretch(); self.body.addLayout(row)
        f,l=card("Список заданий"); self.tasks=table(["ID","Тип задания","Статус","Срок","Поле","Проблемная зона","Исполнитель"]); l.addWidget(self.tasks,1); self.body.addWidget(f,1)
        row=QHBoxLayout(); row.addWidget(btn("Создать задание",self.create_task,True)); row.addWidget(btn("Изменить статус",self.change_status)); row.addWidget(btn("Обновить список",self.refresh)); row.addWidget(btn("Открыть зону задания",self.open_zone)); row.addWidget(btn("К карте",lambda:s.navigate("W1"))); self.body.addLayout(row); self.refresh()
    def showTasks(self,tasks):
        self.tasks.setRowCount(0)
        for t in tasks: add_row(self.tasks,[t['id'],t['task_type'],t['status'],t['deadline'],t.get('field_id','—'),t['problem_area_id'],t.get('executor_name','')])
    def showTaskForm(self): self.create_task()
    def on_show(self):
        self.refresh()

    def apply_search(self,query):
        for row in range(self.tasks.rowCount()):
            values=[self.tasks.item(row,col).text().lower() if self.tasks.item(row,col) else "" for col in range(self.tasks.columnCount())]
            self.tasks.setRowHidden(row,bool(query) and not any(query in value for value in values))

    def refresh(self):
        if not hasattr(self,'tasks'):return
        rows=self.s.c.resolve(TaskController).getPendingTasks(self.status.currentText()); self.tasks.setRowCount(0)
        for t in rows: add_row(self.tasks,[t['id'],t['task_type'],t['status'],t['deadline'],t.get('field_id','—'),t['problem_area_id'],t.get('executor_name','')])
    def create_task(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        d=QDialog(self); d.setWindowTitle("Новое задание"); form=QFormLayout(d); typ=QComboBox(); typ.addItems(["Полив","Подкормка","Защитная обработка","Проверка участка"]); deadline=QDateEdit(); deadline.setCalendarPopup(True); deadline.setDate(QDate.currentDate().addDays(1)); zone=QComboBox()
        zones=self.s.c.resolve(CropMonitoringController).getProblemAreas()
        for z in zones: zone.addItem(f"{z['id']} — {z['problem_type']}",z['id'])
        form.addRow("Тип задания",typ); form.addRow("Срок выполнения",deadline); form.addRow("Проблемная зона",zone); buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); form.addRow(buttons)
        if d.exec():
            z=zone.currentData()
            if not z:
                QMessageBox.warning(self,"Задание","Сначала необходимо зарегистрировать проблемную зону."); return
            self.s.c.resolve(TaskController).createTask({'id':'T-'+__import__('uuid').uuid4().hex[:6].upper(),'task_type':typ.currentText(),'status':'Новое','deadline':deadline.date().toString('yyyy-MM-dd'),'agronomist_id':self.s.user['id'],'problem_area_id':z}); self.refresh()
    def open_zone(self):
        row=self.tasks.currentRow()
        if row<0: QMessageBox.information(self,"Задания","Выберите задание."); return
        self.s.selected_zone_id=self.tasks.item(row,5).text()
        self.s.navigate("W2")
    def change_status(self):
        tid=selected_id(self.tasks)
        if not tid: QMessageBox.information(self,"Задания","Выберите задание."); return
        status,ok=__import__('PyQt6.QtWidgets',fromlist=['QInputDialog']).QInputDialog.getItem(self,"Статус","Новый статус:",["Новое","В работе","Выполнено"],0,False)
        if ok:self.s.c.resolve(TaskController).updateTaskStatus(tid,status); self.refresh()

class InspectionPage(Page,IInspectionView):
    """W4. Scout submits field inspection; agronomist sees it in W1/W2."""
    def __init__(self,s):
        super().__init__(s,"🌱  Полевое обследование")
        f,l=card("Координаты проблемной зоны"); self.zone=QComboBox(); self.zones=s.c.resolve(InspectionController).getProblemZoneCoordinates()
        for z in self.zones:self.zone.addItem(f"{z['id']} • {z['field_id']} • {z['problem_type']} ({z['coordinates']})",z)
        self.zone_info=label("Выберите проблемную зону"); self.zone.currentIndexChanged.connect(self.update_zone)
        l.addWidget(self.zone); l.addWidget(self.zone_info); self.body.addWidget(f)
        f,l=card("Результат полевого обследования"); form=QFormLayout(); self.date=QDateEdit(); self.date.setCalendarPopup(True); self.date.setDate(QDate.currentDate())
        self.condition=QComboBox(); self.condition.addItems(["Норма","Удовлетворительное","Требует вмешательства","Критическое"])
        self.description=QTextEdit(); self.description.setPlaceholderText("Результаты полевого обследования…"); self.description.setMaximumHeight(95)
        self.photo=QLineEdit(); self.photo.setPlaceholderText("Путь к фотоотчёту (необязательно)"); browse=btn("Обзор…",self.browse)
        form.addRow("Дата/время осмотра",self.date); form.addRow("Состояние растений",self.condition); form.addRow("Описание / замечания",self.description)
        photo_row=QHBoxLayout(); photo_row.addWidget(self.photo); photo_row.addWidget(browse); form.addRow("Фото-отчёт",photo_row); l.addLayout(form); self.body.addWidget(f,1)
        self._saved_inspection=False
        row=QHBoxLayout()
        row.addWidget(btn("Сохранить результат",self.save,True))
        row.addWidget(btn("Подтвердить обследование",self.confirm_and_return))
        row.addWidget(btn("Скорректировать участок",self.correct_area))
        row.addStretch()
        self.body.addLayout(row); self.update_zone()
    def showZoneCoordinates(self,zones): self.zone_info.setText("\n".join(z['coordinates'] for z in zones))
    def submitInspectionForm(self,inspection): self.save()
    def on_show(self):
        self.zones=self.s.c.resolve(InspectionController).getProblemZoneCoordinates(); current=self.zone.currentData(); self.zone.clear()
        for z in self.zones:self.zone.addItem(f"{z['id']} • {z['field_id']} • {z['problem_type']} ({z['coordinates']})",z)
        for i in range(self.zone.count()):
            if self.zone.itemData(i) and current and self.zone.itemData(i)['id']==current['id']: self.zone.setCurrentIndex(i)
        self.update_zone()
    def update_zone(self):
        z=self.zone.currentData(); self.zone_info.setText(f"Координаты: {z['coordinates']}    Поле: {z['field_id']}" if z else "Нет проблемных зон")
    def browse(self):
        p,_=QFileDialog.getOpenFileName(self,"Выбрать фотоотчёт","","Изображения (*.png *.jpg *.jpeg);;Все файлы (*)")
        if p:self.photo.setText(p)
    def save(self):
        z=self.zone.currentData()
        if not z: QMessageBox.warning(self,"Обследование","Нет зоны для обследования."); return False
        data={'id':'I-'+__import__('uuid').uuid4().hex[:6].upper(),'timestamp':self.date.date().toString('yyyy-MM-dd'),
              'coordinates':z['coordinates'],'description':self.condition.currentText()+". "+self.description.toPlainText().strip(),
              'photo_report':self.photo.text(),'field_id':z['field_id'],'inspector_id':self.s.user['id'],'problem_area_id':z['id']}
        self.s.c.resolve(InspectionController).registerInspection(data)
        self.s.c.resolve(CropMonitoringController).updateProblemArea(z['id'],'Подтверждена')
        self.description.clear(); self.photo.clear()
        self._saved_inspection=True
        QMessageBox.information(self,"Результат отправлен","Результат обследования сохранён. Агроном увидит его в карточке соответствующей зоны W2.")
        self.zones=self.s.c.resolve(InspectionController).getProblemZoneCoordinates(); self.update_zone()
        return True

    def _return_to_zone(self):
        z=self.zone.currentData()
        if z:
            self.s.selected_zone_id=z['id']
        self.s.navigate("W2")

    def confirm_and_return(self):
        if not self._saved_inspection and not self.save():
            return
        self._return_to_zone()

    def correct_area(self):
        # Correction is a navigation action in the state diagram; it must not
        # be blocked by the requirement to save an inspection first.
        if not self.zone.currentData():
            QMessageBox.information(self,"Корректировка участка","Выберите проблемную зону.")
            return
        self._return_to_zone()

class EquipmentPage(Page,IEquipmentMonitoringView):
    """W5. Equipment screen arranged like the supplied engineer mock-up."""
    def __init__(self,s):
        super().__init__(s,"🌱  Контроль оборудования")
        grid=QGridLayout(); grid.setColumnStretch(0,3); grid.setColumnStretch(1,7); grid.setRowStretch(0,1); self.body.addLayout(grid,1)
        left=QVBoxLayout(); left.setSpacing(8)
        f,l=card("Полевые датчики")
        self.sensors=table(["Датчик","Тип","Координаты","Поле","Статус"]); self.sensors.setMinimumHeight(170); l.addWidget(self.sensors,1); left.addWidget(f,1)
        f,l=card("Сельхозтехника (GPS)")
        self.gps=table(["Техника","Тип","GPS","Статус","Топливо"]); self.gps.setMinimumHeight(150)
        l.addWidget(self.gps,1); left.addWidget(f,1); grid.addLayout(left,0,0)

        f,l=card("Сводка состояния")
        self.summary=QVBoxLayout(); self.summary.setSpacing(7); l.addLayout(self.summary,1); grid.addWidget(f,0,1)
        row=QHBoxLayout(); row.addWidget(btn("Настроить датчик",self.configure,True)); row.addWidget(btn("Сообщить о сбое",self.fault,False,True)); row.addWidget(btn("Запланировать ремонт",self.repair,False)); row.addWidget(btn("Интегрировать сенсор в технику",self.integrate,False)); self.body.addLayout(row)
        self.refresh()

    def apply_search(self,query):
        for widget in (self.sensors,self.gps):
            for row in range(widget.rowCount()):
                values=[widget.item(row,col).text().lower() if widget.item(row,col) else "" for col in range(widget.columnCount())]
                widget.setRowHidden(row,bool(query) and not any(query in value for value in values))

    def showSensorStatus(self,sensors):
        self.sensors.setRowCount(0)
        for x in sensors:add_row(self.sensors,[x['id'],x['type'],x.get('coordinates','—'),x['field_id'],x['status']])
    def showFaultAlert(self,sensorid,description): QMessageBox.warning(self,"Неисправность",f"{sensorid}: {description}")
    def on_show(self):
        self.refresh()

    def refresh(self):
        if not hasattr(self,'sensors'):return
        rows=self.s.c.resolve(EquipmentMonitoringController).getSensors(); self.sensors.setRowCount(0)
        for x in rows:add_row(self.sensors,[x['id'],x['type'],x.get('coordinates','—'),x['field_id'],x['status']])
        machinery=self.s.c.resolve(EquipmentMonitoringController).getMachinery()
        self.gps.setRowCount(0)
        for item in machinery:add_row(self.gps,[item['name'],item['type'],item.get('gps','—'),item.get('status','—'),f"{item.get('fuel',0):g}%"])
        while self.summary.count():
            item=self.summary.takeAt(0)
            if item.widget():item.widget().deleteLater()
        online=sum(1 for x in rows if x['status']=='Работает')
        faulty=sum(1 for x in rows if x['status']!='Работает')
        low_battery=sum(1 for x in rows if float(x.get('battery') or 0)<20)
        values=[("Онлайн:",f"{online} / {len(rows)}"),("Неисправно:",str(faulty)),("Батарея < 20%:",str(low_battery))]
        for title,value in values:
            tile=QFrame(); tile.setStyleSheet("QFrame{background:#ededed;border:1px dashed #bfc3c7;}")
            lay=QHBoxLayout(tile); lay.setContentsMargins(12,8,12,8); lay.addWidget(label(title)); val=label(value); val.setAlignment(Qt.AlignmentFlag.AlignCenter); val.setStyleSheet("color:#53606c;font-size:13pt")
            lay.addWidget(val,1); self.summary.addWidget(tile,1)
    def configure(self):
        sid=selected_id(self.sensors)
        if not sid:
            QMessageBox.information(self,"Датчик","Выберите датчик.")
            return
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        row=self.sensors.currentRow()
        dialog=QDialog(self); dialog.setWindowTitle(f"Настройка датчика {sid}")
        form=QFormLayout(dialog)
        typ=QLineEdit(self.sensors.item(row,1).text())
        coords=QLineEdit(self.sensors.item(row,2).text())
        status=QComboBox(); status.addItems(["Работает","Выключен","В ремонте","Требует проверки","Неисправен"])
        current=self.sensors.item(row,4).text()
        index=status.findText(current)
        if index >= 0: status.setCurrentIndex(index)
        form.addRow("Тип датчика",typ); form.addRow("Координаты",coords); form.addRow("Состояние",status)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec():
            if not typ.text().strip():
                QMessageBox.warning(self,"Настройка датчика","Укажите тип датчика.")
                return
            controller=self.s.c.resolve(EquipmentMonitoringController)
            controller.configureSensor(sid,typ.text().strip(),coords.text().strip())
            controller.setSensorStatus(sid,status.currentText())
            self.refresh()
    def fault(self):
        sid=selected_id(self.sensors)
        if not sid:QMessageBox.information(self,"Датчик","Выберите датчик.");return
        from PyQt6.QtWidgets import QInputDialog
        desc,ok=QInputDialog.getText(self,"Неисправность","Описание технического сбоя:")
        if ok and desc:self.s.c.resolve(EquipmentMonitoringController).reportFault(sid,desc);self.refresh()
    def repair(self):
        sid=selected_id(self.sensors)
        if not sid:QMessageBox.information(self,"Ремонт","Выберите датчик.");return
        self.s.c.resolve(EquipmentMonitoringController).scheduleRepair(sid);self.refresh()
    def integrate(self):
        sid=selected_id(self.sensors)
        if not sid:
            QMessageBox.information(self,"Интеграция","Сначала выберите датчик в таблице."); return
        controller=self.s.c.resolve(EquipmentMonitoringController)
        machines=controller.getMachinery()
        if not machines:
            QMessageBox.warning(self,"Интеграция","В системе пока нет зарегистрированной техники."); return
        from PyQt6.QtWidgets import QInputDialog
        labels=[f"{m['name']} — {m['type']} ({m.get('gps') or 'GPS не задан'})" for m in machines]
        selected,ok=QInputDialog.getItem(self,"Интеграция сенсора в технику","Выберите технику:",labels,0,False)
        if not ok:return
        machine=machines[labels.index(selected)]
        try:
            controller.integrateSensor(sid,machine['id'])
            QMessageBox.information(self,"Интеграция",f"Датчик {sid} связан с объектом «{machine['name']}».")
        except Exception as e:
            QMessageBox.warning(self,"Интеграция",f"Не удалось связать датчик с техникой: {e}")

class ReportsPage(Page,IReportView):
    """W6. Shared analytics view for Analyst and Agronomist."""
    def __init__(self,s):
        super().__init__(s,"🌱  Отчёты и аналитика")
        filters=QHBoxLayout(); self.start_date=QDateEdit(); self.start_date.setCalendarPopup(True); self.start_date.setDisplayFormat("dd.MM.yyyy"); self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date=QDateEdit(); self.end_date.setCalendarPopup(True); self.end_date.setDisplayFormat("dd.MM.yyyy"); self.end_date.setDate(QDate.currentDate())
        self.field_filter=QComboBox(); self.field_filter.addItem("все / выбор","Все")
        for f in self.s.c.resolve(CropMonitoringController).getFieldsOverview():self.field_filter.addItem(f['id'],f['id'])
        self.metric_filter=QComboBox(); self.metric_filter.addItems(["влажность, темп., NPK","Влажность","Температура","Освещённость","NPK"])
        filters.addWidget(label("Период:")); filters.addWidget(self.start_date); filters.addWidget(label("—")); filters.addWidget(self.end_date)
        filters.addWidget(label("Поля:")); filters.addWidget(self.field_filter); filters.addWidget(label("Показатели:")); filters.addWidget(self.metric_filter)
        filters.addWidget(btn("Применить",self.refresh,True)); self.body.addLayout(filters)

        grid=QGridLayout(); grid.setColumnStretch(0,1); grid.setColumnStretch(1,1); self.body.addLayout(grid,2)
        f,l=card("Сводный график по полям"); self.health_chart=SimpleBarChart("Агрегированные индексы состояния")
        l.addWidget(self.health_chart,1); grid.addWidget(f,0,0)
        f,l=card("Распределение проблем"); self.problem_chart=SimpleBarChart("Проблемы по типам")
        l.addWidget(self.problem_chart,1); grid.addWidget(f,0,1)

        f,l=card("Исторические данные")
        self.history=table(["Период","Поле","Ср. индекс","Проблем выявлено","Заданий","Эффективность"])
        self.history.setMinimumHeight(145); l.addWidget(self.history,1); self.body.addWidget(f,2)
        row=QHBoxLayout()
        self.generate_button=btn("Сформировать отчёт",self.make_report,True)
        self.pdf_button=btn("Экспорт PDF",lambda:self.export_report("pdf"))
        self.excel_button=btn("Экспорт Excel",lambda:self.export_report("xlsx"))
        self.planning_button=btn("Планирование ресурсов",self.plan_resources,False)
        for w in (self.generate_button,self.pdf_button,self.excel_button,self.planning_button):row.addWidget(w)
        row.addStretch(); self.body.addLayout(row)
        # The UI state diagram permits the agronomist to open W6, while report generation
        # and resource planning belong to the analyst's use cases.
        if self.s.user['role']=="Агроном":
            for w in (self.generate_button,self.pdf_button,self.excel_button,self.planning_button):
                w.setEnabled(False); w.setToolTip("Формирование отчётов и планирование ресурсов — функция аналитика")
        self.last_report_id=None; self.refresh()

    def showReport(self,report):QMessageBox.information(self,"Отчёт",report.get('content',''))
    def exportReport(self,report,format):return self.s.c.resolve(ReportController).exportReport(report['id'],format)

    def _filtered_data(self):
        start=self.start_date.date().toString("yyyy-MM-dd"); end=self.end_date.date().toString("yyyy-MM-dd")
        field_id=self.field_filter.currentData(); metric=self.metric_filter.currentText()
        readings=self.s.c.resolve(SensorReadingRepository).getReadings("", "")
        readings=[r for r in readings if start<=r['reading_time'][:10]<=end]
        if field_id!="Все":readings=[r for r in readings if r['field_id']==field_id]
        if metric!="влажность, темп., NPK":
            readings=[r for r in readings if metric.lower() in r['type'].lower() or (metric=="NPK" and "пит" in r['type'].lower())]
        fields=self.s.c.resolve(CropMonitoringController).getFieldsOverview()
        if field_id!="Все":fields=[f for f in fields if f['id']==field_id]
        return start,end,field_id,metric,readings,fields

    @staticmethod
    def _index(readings):
        if not readings:return 0.0
        values=[float(r['value']) for r in readings]
        # The specification contains no formula; this transparent demo indicator is documented as an implementation assumption.
        return round(max(0.0,min(1.0,(100-sum(abs(v-60) for v in values)/len(values))/100)),2)

    def on_show(self):
        self.refresh()

    def refresh(self):
        if not hasattr(self,'history'):return
        start,end,field_id,metric,readings,fields=self._filtered_data()
        zones=self.s.c.resolve(CropMonitoringController).getProblemAreas(); tasks=self.s.c.resolve(TaskRepository).getTasksByStatus("Все")
        health_labels=[]; health_values=[]; self.history.setRowCount(0)
        for f in fields:
            field_readings=[r for r in readings if r['field_id']==f['id']]
            index=self._index(field_readings); health_labels.append(f['id']); health_values.append(index)
            field_zones=[z for z in zones if z['field_id']==f['id']]
            field_tasks=[t for t in tasks if t.get('field_id')==f['id']]
            completed=sum(1 for t in field_tasks if t['status']=="Выполнено")
            efficiency=f"{completed/len(field_tasks)*100:.0f}%" if field_tasks else "—"
            add_row(self.history,[f"{start[8:10]}.{start[5:7]}.{start[:4]}–{end[8:10]}.{end[5:7]}.{end[:4]}",f['id'],f"{index:.2f}",len(field_zones),len(field_tasks),efficiency])
        self.health_chart.set_data(health_labels,health_values,"Индекс состояния (0–1)")
        counts={}
        for z in zones:
            if field_id=="Все" or z['field_id']==field_id:counts[z['problem_type']]=counts.get(z['problem_type'],0)+1
        self.problem_chart.set_data(list(counts),list(counts.values()),"Количество проблемных зон")

    def _generate_current_report(self):
        start,end,field_id,metric,readings,fields=self._filtered_data()
        period=f"{start} — {end}"
        return self.s.c.resolve(ReportController).generateReport(period, [f['id'] for f in fields], self.s.user['id'])

    def make_report(self):
        try:
            r=self._generate_current_report(); self.last_report_id=r['id']
            self.refresh()
            QMessageBox.information(self,"Отчёт",f"Отчёт {r['id']} сохранён. Он доступен для просмотра в ведомственном контроле.")
        except Exception as e:
            QMessageBox.warning(self,"Отчёт не создан",f"Не удалось сформировать отчёт. Проверьте выбранный период и данные.\n\nТехническая ошибка: {e}")

    def export_report(self,fmt):
        path,selected=QFileDialog.getSaveFileName(self,"Экспорт отчёта",f"plant_report.{fmt}",f"{fmt.upper()} (*.{fmt})")
        if not path:return
        try:
            report=self.s.c.resolve(ReportRepository).getById(self.last_report_id) if self.last_report_id else None
            if not report:report=self._generate_current_report(); self.last_report_id=report['id']
            generated_path=self.s.c.resolve(ReportController).exportReport(report['id'],fmt,path)
            QMessageBox.information(self,"Экспорт",f"Файл сохранён:\n{generated_path}")
        except Exception as e:QMessageBox.warning(self,"Экспорт недоступен",f"Не удалось экспортировать отчёт.\n\nТехническая ошибка: {e}")

    def plan_resources(self):
        start,end,field_id,metric,readings,fields=self._filtered_data()
        QMessageBox.information(self,"Планирование ресурсов",f"Период: {start} — {end}\nПолей: {len(fields)}\nПоказаний: {len(readings)}\nЗаданий: {len(self.s.c.resolve(TaskRepository).getTasksByStatus("Все"))}\n\nСводные данные подготовлены для планирования ресурсов.")

class GovernmentPage(Page):
    """W7. Government reads reports created by the analyst."""
    def __init__(self,s):
        super().__init__(s,"🌱  Контроль землепользования")
        grid=QGridLayout(); grid.setColumnStretch(0,3); grid.setColumnStretch(1,2); self.body.addLayout(grid,1)
        f,l=card("Агрегированная карта земель"); self.map=label("СОСТОЯНИЕ СЕЛЬХОЗУГОДИЙ ПО РЕГИОНАМ\n\n(демонстрационное представление)")
        self.map.setAlignment(Qt.AlignmentFlag.AlignCenter); self.map.setStyleSheet("background:#ededed;color:#68727c;min-height:280px;border:1px dashed #bfc3c7")
        l.addWidget(self.map,1); grid.addWidget(f,0,0,2,1)
        f,l=card("Экологический мониторинг"); self.eco=label("Сводка по нагрузке / нарушениям"); self.eco.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eco.setStyleSheet("background:#ededed;color:#68727c;min-height:120px;border:1px dashed #bfc3c7"); l.addWidget(self.eco,1); grid.addWidget(f,0,1)
        f,l=card("Отчётность предприятий"); self.reports=table(["Период","Отчёт","Автор"]); l.addWidget(self.reports,1); grid.addWidget(f,1,1)
        row=QHBoxLayout(); row.addWidget(btn("Просмотреть отчёт",self.view_report,True)); row.addWidget(btn("Выгрузить агрегированные данные",self.export)); row.addStretch(); self.body.addLayout(row); self.refresh()

    def on_show(self):
        self.refresh()

    def apply_search(self,query):
        for row in range(self.reports.rowCount()):
            values=[self.reports.item(row,col).text().lower() if self.reports.item(row,col) else "" for col in range(self.reports.columnCount())]
            self.reports.setRowHidden(row,bool(query) and not any(query in value for value in values))

    def refresh(self):
        if not hasattr(self,'reports'):return
        rows=self.s.c.resolve(ReportController).getReports(""); self.reports.setRowCount(0)
        for r in rows:
            n=self.reports.rowCount(); add_row(self.reports,[r['period'],r['id'],r.get('author_name','')])
            self.reports.item(n,0).setData(Qt.ItemDataRole.UserRole,r['id'])
        zones=self.s.c.resolve(CropMonitoringController).getProblemAreas()
        self.eco.setText(f"Всего проблемных зон: {len(zones)}\nПодтверждено: {sum(1 for z in zones if z['status']=='Подтверждена')}\nОткрыто: {sum(1 for z in zones if z['status'] in ('Открыта','Выявлена'))}")

    def view_report(self):
        row=self.reports.currentRow()
        if row<0:QMessageBox.information(self,"Отчёты","Выберите отчёт в таблице.");return
        report_id=self.reports.item(row,0).data(Qt.ItemDataRole.UserRole)
        report=self.s.c.resolve(ReportRepository).getById(report_id)
        if not report:QMessageBox.warning(self,"Отчёты","Выбранный отчёт отсутствует в базе данных. Обновите список.");return
        from PyQt6.QtWidgets import QDialog,QDialogButtonBox
        d=QDialog(self); d.setWindowTitle(f"Отчёт {report['id']}"); d.resize(620,460); lay=QVBoxLayout(d)
        lay.addWidget(label(f"Период: {report['period']}",'sectionTitle'))
        content=QTextEdit(); content.setReadOnly(True); content.setPlainText(report['content']); lay.addWidget(content,1)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(d.reject); buttons.accepted.connect(d.accept); lay.addWidget(buttons); d.exec()

    def export(self):
        path,_=QFileDialog.getSaveFileName(self,"Экспорт агрегированных данных","land_monitoring.csv","CSV (*.csv)")
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f,delimiter=';');w.writerow(["ID зоны","Поле","Тип проблемы","Статус"])
            for z in self.s.c.resolve(CropMonitoringController).getProblemAreas():w.writerow([z['id'],z['field_id'],z['problem_type'],z['status']])
        QMessageBox.information(self,"Экспорт","Агрегированные данные выгружены.")
