import tkinter as tk
from tkinter import ttk, messagebox

# --- КОНФИГУРАЦИЯ И КОНСТАНТЫ ---
GATE_WIDTH = 70
GATE_HEIGHT = 50
PORT_RADIUS = 6
TRASH_HEIGHT = 60

SIDEBAR_WIDTH = 260   # Увеличена ширина для крупных кнопок
TABLE_WIDTH = 200     # Ширина правой панели с таблицей

# Цветовая палитра (Темная тема)
COLOR_LOW = "#FF4444"    # Красный (Логический 0)
COLOR_HIGH = "#44FF44"   # Зеленый (Логическая 1)
COLOR_GATE = "#444444"   # Темно-серый (Тело вентиля)
COLOR_BG = "#1e1e1e"     # Фон холста
COLOR_PANEL = "#2b2b2b"  # Фон панелей (боковых)
COLOR_WIRE = "#00BFFF"   # Цвет проводов (Cyan)
COLOR_HOVER = "#FF0000"  # Цвет при наведении на провод
COLOR_BTN = "#555555"    # Цвет кнопок
COLOR_BTN_ACTIVE = "#6E6E6E" # Цвет нажатой кнопки

MAX_INPUTS = 8 
MAX_OUTPUTS = 3

LOGIC_TYPES_2_INPUT = ('AND', 'NAND', 'NOR', 'OR', 'XNOR', 'XOR')
LOGIC_TYPES_1_INPUT = ('NOT',)

# --- ШРИФТЫ ---
# Verdana красивый, читаемый и хорошо смотрится в интерфейсах
BTN_FONT = ('Verdana', 11, 'bold')   # Крупный, жирный для кнопок
HEADER_FONT = ('Verdana', 11, 'bold') # Заголовки
TEXT_FONT = ('Verdana', 10)          # Обычный текст
GATE_FONT = ('Verdana', 10, 'bold')  # Текст внутри блоков

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=15, **kwargs):
    """Рисует скругленный прямоугольник"""
    points = [
        x1+radius, y1,
        x2-radius, y1,
        x2, y1, x2, y1+radius,
        x2, y2-radius,
        x2, y2, x2-radius, y2,
        x1+radius, y2,
        x1, y2, x1, y2-radius,
        x1, y1+radius,
        x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

# --- КЛАССЫ ЛОГИКИ ---

class LogicGate:
    """Класс, описывающий логический блок"""
    def __init__(self, g_type, x, y, uid, name=None):
        self.g_type = g_type
        self.x = x
        self.y = y
        self.uid = uid
        self.name = name
        self.value = False 
        
        self.rect_id = None
        self.text_id = None
        self.port_ids = [] 
        
        if g_type in LOGIC_TYPES_1_INPUT or g_type == 'OUTPUT':
            self.inputs = [False]
        elif g_type in LOGIC_TYPES_2_INPUT:
            self.inputs = [False, False]
        else:
            self.inputs = []

    def evaluate(self):
        v = self.inputs
        
        if self.g_type == 'INPUT': return self.value
        if self.g_type == 'OUTPUT':
            self.value = v[0]
            return self.value

        if self.g_type == 'NOT': return not v[0]
        
        A, B = v[0], v[1]
        
        if self.g_type == 'AND': return A and B
        elif self.g_type == 'OR': return A or B
        elif self.g_type == 'NAND': return not (A and B)
        elif self.g_type == 'NOR': return not (A or B)
        elif self.g_type == 'XOR': return A != B
        elif self.g_type == 'XNOR': return A == B
        
        return False

    def get_input_pos(self, index):
        total_inputs = len(self.inputs)
        if total_inputs == 0: return None
        step = GATE_HEIGHT / (total_inputs + 1)
        py = self.y + step * (index + 1)
        return (self.x, py)

    def get_output_pos(self):
        if self.g_type == 'OUTPUT': return None
        return (self.x + GATE_WIDTH, self.y + GATE_HEIGHT / 2)


class Connection:
    """Класс, описывающий соединение"""
    def __init__(self, from_gate, to_gate, to_idx, line_id):
        self.from_gate = from_gate
        self.to_gate = to_gate
        self.to_idx = to_idx
        self.line_id = line_id


# --- ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ---

class CircuitApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Симулятор Логических Схем")
        self.root.geometry("1400x750") # Чуть увеличил ширину окна

        # Настройка стиля Treeview для темной темы
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Treeview", 
                             foreground="white", 
                             background="#333333", 
                             font=TEXT_FONT, 
                             rowheight=24,
                             fieldbackground="#333333",
                             borderwidth=0)
        self.style.configure("Treeview.Heading", 
                             font=HEADER_FONT, 
                             foreground="white", 
                             background="#444444",
                             borderwidth=0)
        self.style.map("Treeview", background=[('selected', '#005577')])

        self.gates = []
        self.connections = []
        self.gate_counter = 0
        
        self.available_input_names = sorted(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        self.used_input_names = []
        self.drag_data = {"item": None, "x": 0, "y": 0, "type": None, "start_gate": None}
        self.temp_line = None

        self.setup_ui()

    def setup_ui(self):
        # --- ЛЕВАЯ ПАНЕЛЬ (Кнопки) ---
        self.sidebar_frame = tk.Frame(self.root, width=SIDEBAR_WIDTH, bg=COLOR_PANEL, padx=5, pady=5)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        btns_frame = tk.Frame(self.sidebar_frame, bg=COLOR_PANEL)
        btns_frame.pack(fill="x", pady=5)

        # Кнопки (крупные, прямоугольные)
        self.create_btn(btns_frame, "ВХОД (INPUT)", lambda: self.create_gate("INPUT"))
        self.create_btn(btns_frame, "ВЫХОД (OUTPUT)", lambda: self.create_gate("OUTPUT"))
        
        # ЗАГОЛОВОК: Логические вентили
        tk.Label(btns_frame, text="Логические вентили", bg=COLOR_PANEL, fg="white", font=HEADER_FONT).pack(pady=(15, 8))
        
        self.create_btn(btns_frame, "И (AND)", lambda: self.create_gate("AND"))
        self.create_btn(btns_frame, "НЕ-И (NAND)", lambda: self.create_gate("NAND"))
        self.create_btn(btns_frame, "НЕ-ИЛИ (NOR)", lambda: self.create_gate("NOR"))
        self.create_btn(btns_frame, "НЕ (NOT)", lambda: self.create_gate("NOT"))
        self.create_btn(btns_frame, "ИЛИ (OR)", lambda: self.create_gate("OR"))
        self.create_btn(btns_frame, "ИСКЛ. НЕ-ИЛИ (XNOR)", lambda: self.create_gate("XNOR"))
        self.create_btn(btns_frame, "ИСКЛ. ИЛИ (XOR)", lambda: self.create_gate("XOR"))

        # ЗАГОЛОВОК: Действия
        tk.Label(btns_frame, text="Действия", bg=COLOR_PANEL, fg="white", font=HEADER_FONT).pack(pady=(15, 8))
        self.create_btn(btns_frame, "УДАЛИТЬ ВСЮ СХЕМУ", self.clear_all_scheme, color="#AA4444")

        # Счетчики
        self.lbl_counters = tk.Label(self.sidebar_frame, text="", bg=COLOR_PANEL, fg="white", justify="left", font=TEXT_FONT)
        self.lbl_counters.pack(pady=15)
        self.update_counters()

        # --- ПРАВАЯ ЧАСТЬ (Холст + Таблица) ---
        self.right_container = tk.Frame(self.root, bg=COLOR_PANEL)
        self.right_container.pack(side="right", fill="both", expand=True)

        # 1. Холст (в центре)
        self.canvas = tk.Canvas(self.right_container, bg=COLOR_BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.draw_trash_can()

        # 2. Панель Таблицы Истинности (справа)
        self.table_panel = tk.Frame(self.right_container, width=TABLE_WIDTH, bg=COLOR_PANEL, padx=5, pady=5)
        self.table_panel.pack(side="right", fill="y")
        self.table_panel.pack_propagate(False)

        tk.Label(self.table_panel, text="Таблица\nИстинности", bg=COLOR_PANEL, fg="white", font=HEADER_FONT, justify="center").pack(pady=(0, 5))
        
        tt_container = tk.Frame(self.table_panel, bg="white", bd=1, relief="solid")
        tt_container.pack(fill="both", expand=True)
        
        vsb = ttk.Scrollbar(tt_container, orient="vertical")
        self.tree = ttk.Treeview(tt_container, columns=[], show="headings", yscrollcommand=vsb.set, selectmode="none")
        vsb.config(command=self.tree.yview)
        
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # Привязки событий
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def create_btn(self, parent, text, command, color=None):
        """Создает крупную прямоугольную кнопку"""
        bg_color = color if color else COLOR_BTN
        
        btn = tk.Button(parent, text=text, command=command, 
                         bg=bg_color, fg="white", 
                         activebackground=COLOR_BTN_ACTIVE, 
                         relief="flat", # Плоский стиль для современности
                         bd=0,
                         font=BTN_FONT, 
                         pady=10)       # Большой отступ для высоты
        btn.pack(fill="x", pady=4)     # Отступ между кнопками

    def draw_trash_can(self):
        self.trash_rect = self.canvas.create_rectangle(0, 0, 0, 0, fill="#440000", outline="", tags="trash")
        self.trash_text = self.canvas.create_text(0, 0, text="УДАЛИТЬ (Trash)", fill="#FF5555", font=GATE_FONT, tags="trash")
        self.canvas.bind("<Configure>", self.resize_trash)

    def resize_trash(self, event):
        self.canvas.coords(self.trash_rect, 0, event.height - TRASH_HEIGHT, event.width, event.height)
        self.canvas.coords(self.trash_text, event.width/2, event.height - TRASH_HEIGHT/2)

    def clear_all_scheme(self):
        temp_gates = self.gates[:] 
        for gate in reversed(temp_gates):
            self.delete_gate(gate)
        
        self.gates = []
        self.connections = []
        self.gate_counter = 0
        self.used_input_names = []
        self.available_input_names = sorted(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        
        self.update_counters()
        self.update_truth_table()
        
    def create_gate(self, g_type):
        inputs = [g for g in self.gates if g.g_type == 'INPUT']
        outputs = [g for g in self.gates if g.g_type == 'OUTPUT']

        if g_type == 'INPUT':
            if len(inputs) >= MAX_INPUTS:
                messagebox.showwarning("Лимит", f"Максимум {MAX_INPUTS} входов!")
                return
            name = self.available_input_names.pop(0)
            self.used_input_names.append(name)
            self.used_input_names.sort()
        
        elif g_type == 'OUTPUT':
            if len(outputs) >= MAX_OUTPUTS:
                messagebox.showwarning("Лимит", f"Максимум {MAX_OUTPUTS} выходов!")
                return
            name = f"Out{len(outputs)+1}"
        else:
            name = g_type

        self.gate_counter += 1
        import random
        offset_x = random.randint(0, 50)
        offset_y = random.randint(0, 50)
        
        gate = LogicGate(g_type, 100 + offset_x, 100 + offset_y, self.gate_counter, name)
        self.gates.append(gate)
        
        self.draw_gate(gate)
        self.update_counters()
        self.run_simulation()

    def draw_gate(self, gate):
        # Начальный цвет
        color = COLOR_LOW
        if gate.g_type not in ['INPUT', 'OUTPUT']:
            color = COLOR_GATE

        main_tag = f"gate_{gate.uid}"
        x1, y1 = gate.x, gate.y
        x2, y2 = gate.x + GATE_WIDTH, gate.y + GATE_HEIGHT

        # СКРУГЛЕННЫЙ ПРЯМОУГОЛЬНИК
        gate.rect_id = create_rounded_rectangle(
            self.canvas, x1, y1, x2, y2,
            radius=15, 
            fill=color, 
            outline="white", 
            width=2, 
            tags=("gate", main_tag)
        )
        
        label = gate.name if gate.g_type == 'INPUT' else ("OUT" if gate.g_type == 'OUTPUT' else gate.g_type)
        
        gate.text_id = self.canvas.create_text(
            (x1+x2)/2, (y1+y2)/2, text=label, fill="white",
            font=GATE_FONT, tags=("gate", main_tag)
        )

        gate.port_ids = []
        for i in range(len(gate.inputs)):
            px, py = gate.get_input_pos(i)
            pid = self.canvas.create_oval(
                px-PORT_RADIUS, py-PORT_RADIUS, px+PORT_RADIUS, py+PORT_RADIUS,
                fill="white", outline="black", tags=("port", f"in_{gate.uid}_{i}", main_tag)
            )
            gate.port_ids.append({'id': pid, 'type': 'in', 'index': i})

        out_pos = gate.get_output_pos()
        if out_pos:
            px, py = out_pos
            pid = self.canvas.create_oval(
                px-PORT_RADIUS, py-PORT_RADIUS, px+PORT_RADIUS, py+PORT_RADIUS,
                fill="black", outline="white", tags=("port", f"out_{gate.uid}", main_tag)
            )
            gate.port_ids.append({'id': pid, 'type': 'out', 'index': 0})

    def delete_gate(self, gate):
        to_remove = [c for c in self.connections if c.from_gate == gate or c.to_gate == gate]
        for conn in to_remove:
            self.delete_connection(conn)

        if gate.g_type == 'INPUT':
            if gate.name in self.used_input_names:
                self.used_input_names.remove(gate.name)
                self.available_input_names.append(gate.name)
                self.available_input_names.sort()

        self.canvas.delete(f"gate_{gate.uid}") 
        
        if gate in self.gates:
            self.gates.remove(gate)
            
        self.update_counters()
        self.run_simulation()

    def delete_connection(self, conn):
        self.canvas.delete(conn.line_id)
        if conn in self.connections:
            self.connections.remove(conn)
        self.run_simulation()

    def update_counters(self):
        cnt_in = len([g for g in self.gates if g.g_type == 'INPUT'])
        cnt_out = len([g for g in self.gates if g.g_type == 'OUTPUT'])
        self.lbl_counters.config(text=f"Входы: {cnt_in}/{MAX_INPUTS}\nВыходы: {cnt_out}/{MAX_OUTPUTS}")

    # --- ИНТЕРАКТИВНОСТЬ (Мышь) ---

    def on_click(self, event):
        # Удаление провода по клику
        clicked_line = self.canvas.find_withtag("current")
        if clicked_line and "wire" in self.canvas.gettags(clicked_line[0]):
            for conn in self.connections:
                if conn.line_id == clicked_line[0]:
                    self.delete_connection(conn)
                    return

        closest = self.canvas.find_closest(event.x, event.y, halo=5)
        if closest:
            tags = self.canvas.gettags(closest[0])
            port_tag = next((t for t in tags if t.startswith("out_")), None)
            
            if port_tag:
                parts = port_tag.split("_")
                uid = int(parts[1])
                gate = next((g for g in self.gates if g.uid == uid), None)
                
                self.drag_data["type"] = "wire"
                self.drag_data["start_gate"] = gate
                pos = gate.get_output_pos()
                self.temp_line = self.canvas.create_line(pos[0], pos[1], event.x, event.y, fill=COLOR_WIRE, width=2, dash=(2,2))
                return

        for gate in self.gates:
            if (gate.x <= event.x <= gate.x + GATE_WIDTH and
                gate.y <= event.y <= gate.y + GATE_HEIGHT):
                
                if gate.g_type == 'INPUT':
                    gate.value = not gate.value
                    self.run_simulation()
                
                self.drag_data["item"] = gate
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                self.drag_data["type"] = "gate"
                return

    def on_drag(self, event):
        if self.drag_data["type"] == "gate":
            gate = self.drag_data["item"]
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            gate.x += dx
            gate.y += dy
            
            self.canvas.move(f"gate_{gate.uid}", dx, dy) 
            
            self.redraw_wires_for_gate(gate)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        elif self.drag_data["type"] == "wire":
            coords = self.canvas.coords(self.temp_line)
            self.canvas.coords(self.temp_line, coords[0], coords[1], event.x, event.y)

    def on_release(self, event):
        if self.drag_data["type"] == "gate":
            gate = self.drag_data["item"]
            if event.y > self.canvas.winfo_height() - TRASH_HEIGHT:
                self.delete_gate(gate)
            self.drag_data["item"] = None
            self.drag_data["type"] = None

        elif self.drag_data["type"] == "wire":
            self.canvas.delete(self.temp_line)
            self.temp_line = None
            
            closest = self.canvas.find_closest(event.x, event.y, halo=10)
            if closest:
                tags = self.canvas.gettags(closest[0])
                port_tag = next((t for t in tags if t.startswith("in_")), None)
                if port_tag:
                    parts = port_tag.split("_")
                    uid, idx = int(parts[1]), int(parts[2])
                    target = next((g for g in self.gates if g.uid == uid), None)
                    source = self.drag_data["start_gate"]
                    
                    if target and source and target != source:
                        existing = next((c for c in self.connections if c.to_gate == target and c.to_idx == idx), None)
                        if existing: self.delete_connection(existing)
                        
                        start = source.get_output_pos()
                        end = target.get_input_pos(idx)
                        lid = self.canvas.create_line(start[0], start[1], end[0], end[1], fill=COLOR_WIRE, width=3, tags="wire")
                        
                        self.canvas.tag_bind(lid, "<Enter>", lambda e, l=lid: self.canvas.itemconfig(l, fill=COLOR_HOVER))
                        self.canvas.tag_bind(lid, "<Leave>", lambda e, l=lid: self.canvas.itemconfig(l, fill=COLOR_WIRE))
                        
                        self.connections.append(Connection(source, target, idx, lid))
                        self.run_simulation()
            self.drag_data["type"] = None

    def redraw_wires_for_gate(self, gate):
        for conn in self.connections:
            if conn.from_gate == gate or conn.to_gate == gate:
                s = conn.from_gate.get_output_pos()
                e = conn.to_gate.get_input_pos(conn.to_idx)
                if s and e: self.canvas.coords(conn.line_id, s[0], s[1], e[0], e[1])

    # --- СИМУЛЯЦИЯ И ТАБЛИЦА ---

    def run_simulation(self):
        self.simulate_logic()
        
        for gate in self.gates:
            if gate.g_type in ['INPUT', 'OUTPUT']:
                color = COLOR_HIGH if gate.value else COLOR_LOW
                self.canvas.itemconfig(gate.rect_id, fill=color)
        
        self.update_truth_table()

    def simulate_logic(self):
        for gate in self.gates:
            if gate.g_type != 'INPUT':
                cnt = 2 if gate.g_type in LOGIC_TYPES_2_INPUT else 1
                gate.inputs = [False] * cnt

        for _ in range(len(self.gates) + 2):
            for conn in self.connections:
                conn.to_gate.inputs[conn.to_idx] = conn.from_gate.evaluate()
            for gate in self.gates:
                gate.evaluate()

    def update_truth_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        inputs_sorted = sorted([g for g in self.gates if g.g_type == 'INPUT'], key=lambda g: g.name)
        outputs_sorted = sorted([g for g in self.gates if g.g_type == 'OUTPUT'], key=lambda g: g.uid)
        
        col_names = [g.name for g in inputs_sorted] + [" | "] + [f"O{i+1}" for i, g in enumerate(outputs_sorted)]
        self.tree["columns"] = col_names
        
        for col in col_names:
            self.tree.heading(col, text=col)
            width = 20 if col != " | " else 10
            self.tree.column(col, width=width, anchor="center", stretch=False)

        if not inputs_sorted: return

        real_states = {g: g.value for g in inputs_sorted}
        
        num_inputs = len(inputs_sorted)
        for i in range(2 ** num_inputs):
            row_vals = []
            
            for j in range(num_inputs):
                val = bool((i >> (num_inputs - 1 - j)) & 1)
                inputs_sorted[j].value = val
                row_vals.append("1" if val else "0")
            
            self.simulate_logic()
            row_vals.append("|")
            
            for out in outputs_sorted:
                row_vals.append("1" if out.value else "0")
            
            self.tree.insert("", "end", values=row_vals)

        for g, val in real_states.items():
            g.value = val
        self.simulate_logic()

if __name__ == "__main__":
    root = tk.Tk()
    app = CircuitApp(root)
    root.mainloop()