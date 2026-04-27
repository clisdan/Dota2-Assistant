import sys
import threading
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# =========================
# SETTINGS
# =========================
settings = QSettings("Clisdan", "Dota2Assistant")

# =========================
# GLOBAL STATE
# =========================
volume_level = int(settings.value("volume", 100))

stack_enabled = settings.value("stack", True, type=bool)
power_rune_enabled = settings.value("power", True, type=bool)
early_timer_enabled = settings.value("drag", False, type=bool)
wisdom_enabled = settings.value("wisdom", True, type=bool)
tormentor_enabled = settings.value("tormentor", True, type=bool)

current_time_text = "0:00"

# trigger guards
last_stack_prepare_minute = -1
last_stack_now_minute = -1
last_power_minute = -1
last_drag_time = (-1, -1)
triggered_events = set()

# =========================
# EVENTS
# =========================
WISDOM_EVENTS = {
    (6,30): "Prepare for Wisdom rune", (7,0): "Wisdom rune spawned",
    (13,30): "Prepare for Wisdom rune", (14,0): "Wisdom rune spawned",
    (20,30): "Prepare for Wisdom rune", (21,0): "Wisdom rune spawned",
    (27,30): "Prepare for Wisdom rune", (28,0): "Wisdom rune spawned",
    (34,30): "Prepare for Wisdom rune", (35,0): "Wisdom rune spawned",
    (41,30): "Prepare for Wisdom rune", (42,0): "Wisdom rune spawned",
    (48,30): "Prepare for Wisdom rune", (49,0): "Wisdom rune spawned",
    (55,30): "Prepare for Wisdom rune", (56,0): "Wisdom rune spawned",
}

TORMENTOR_EVENTS = {
    (19,30): "Prepare for Tormentor",
    (20,0): "Tormentor has spawned"
}

# =========================
# VOICE
# =========================
def speak(text, rate=0):
    vol = int(volume_level)
    os.system(
        f'powershell -c "$v=New-Object -ComObject SAPI.SpVoice;'
        f'$v.Volume={vol};$v.Rate={rate};$v.Speak(\'{text}\')"'
    )

def alert(text, rate=0):
    threading.Thread(target=speak, args=(text, rate)).start()

# =========================
# SERVER
# =========================
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        global last_stack_prepare_minute, last_stack_now_minute
        global last_power_minute, last_drag_time

        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))

        if "map" in data:
            t = data["map"]["clock_time"]

            if t > 0:
                m = int(t // 60)
                s = int(t % 60)

                # STACK
                if stack_enabled:
                    if 34 <= s <= 36 and m != last_stack_prepare_minute:
                        alert("Prepare to stack", 2)
                        last_stack_prepare_minute = m

                    if 50 <= s <= 51 and m != last_stack_now_minute:
                        alert("Stack NOW", 2)
                        last_stack_now_minute = m

                # POWER RUNE
                if power_rune_enabled:
                    if m >= 5 and (m - 5) % 2 == 0 and 28 <= s <= 32:
                        if m != last_power_minute:
                            alert("Power Rune Spawning", 1)
                            last_power_minute = m

                # DRAG
                if early_timer_enabled:
                    if m <= 5 and s in (10, 40):
                        if (m, s) != last_drag_time:
                            alert("Prepare to drag creeps", -1)
                            last_drag_time = (m, s)

                # WISDOM
                if wisdom_enabled:
                    if (m, s) in WISDOM_EVENTS and (m, s) not in triggered_events:
                        alert(WISDOM_EVENTS[(m, s)], 0)
                        triggered_events.add((m, s))

                # TORMENTOR
                if tormentor_enabled:
                    if (m, s) in TORMENTOR_EVENTS and (m, s) not in triggered_events:
                        alert(TORMENTOR_EVENTS[(m, s)], -2)
                        triggered_events.add((m, s))

        self.send_response(200)
        self.end_headers()

# =========================
# CONTROL PANEL
# =========================
class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dota 2 Assistant by clisdan")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Volume"))

        slider = QSlider(Qt.Horizontal)
        slider.setValue(volume_level)
        slider.valueChanged.connect(self.set_volume)
        layout.addWidget(slider)

        def add_chk(name, var, key):
            chk = QCheckBox(name)
            chk.setChecked(globals()[var])

            def update():
                val = chk.isChecked()
                globals()[var] = val
                settings.setValue(key, val)

            chk.stateChanged.connect(update)
            layout.addWidget(chk)

        add_chk("Stack Alerts", "stack_enabled", "stack")
        add_chk("Power Rune Alerts", "power_rune_enabled", "power")
        add_chk("Drag reminder", "early_timer_enabled", "drag")
        add_chk("Wisdom Alerts", "wisdom_enabled", "wisdom")
        add_chk("Tormentor Alerts", "tormentor_enabled", "tormentor")

        self.setLayout(layout)

    def set_volume(self, v):
        global volume_level
        volume_level = v
        settings.setValue("volume", v)

# =========================
# MAIN
# =========================
def run():
    threading.Thread(
        target=lambda: HTTPServer(('127.0.0.1', 3000), Handler).serve_forever(),
        daemon=True
    ).start()

    app = QApplication(sys.argv)

    panel = ControlPanel()
    panel.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    run()