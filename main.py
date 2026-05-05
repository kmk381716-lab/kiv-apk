from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.properties import ListProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle

import jdatetime
from db import init_db, insert_tasks, get_tasks, insert_entry, get_stats_between

MAX_TASKS = 25

def show_popup(message):
    popup = Popup(
        title="پیام",
        content=Label(text=message),
        size_hint=(0.7, 0.3)
    )
    popup.open()

def jalali_to_greg(jalali_str):
    parts = jalali_str.split("/")
    if len(parts) != 3:
        raise ValueError("فرمت تاریخ اشتباه است")
    y, m, d = map(int, parts)
    jd = jdatetime.date(y, m, d)
    return jd.togregorian().strftime("%Y-%m-%d")

def validate_time_to_minutes(hhmm):
    parts = hhmm.split(":")
    if len(parts) != 2:
        raise ValueError("فرمت ساعت اشتباه است")
    h, m = map(int, parts)
    if h < 0 or m < 0 or m > 59:
        raise ValueError("ساعت نامعتبر است")
    return h * 60 + m

class BarChart(BoxLayout):
    labels = ListProperty([])
    values = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_canvas, size=self.update_canvas,
                  labels=self.update_canvas, values=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            Rectangle(pos=self.pos, size=self.size)

        self.canvas.after.clear()
        if not self.values:
            return

        max_val = max(self.values) if max(self.values) > 0 else 1
        bar_width = self.width / max(len(self.values), 1)
        for i, val in enumerate(self.values):
            height = (val / max_val) * (self.height * 0.8)
            x = self.x + i * bar_width + 10
            y = self.y + 10

            with self.canvas.after:
                Color(0.2, 0.7, 0.9, 1)
                Rectangle(pos=(x, y), size=(bar_width - 20, height))

class MainUI(TabbedPanel):
    task_inputs = ListProperty([])
    report_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.time_inputs_map = {}
        Clock.schedule_once(lambda dt: self.refresh_tasks())

    def generate_task_fields(self):
        try:
            count = int(self.ids.task_count.text.strip())
        except:
            show_popup("عدد معتبر وارد کن")
            return

        if count < 1 or count > MAX_TASKS:
            show_popup(f"تعداد باید بین 1 تا {MAX_TASKS} باشد")
            return

        container = self.ids.task_inputs_container
        container.clear_widgets()
        self.task_inputs = []

        for i in range(count):
            ti = TextInput(
                hint_text=f"اسم تسک {i+1}",
                size_hint_y=None,
                height=40,
                halign="right",
                multiline=False
            )
            self.task_inputs.append(ti)
            container.add_widget(ti)

    def save_tasks(self):
        names = [ti.text.strip() for ti in self.task_inputs if ti.text.strip()]
        if not names:
            show_popup("هیچ تسکی وارد نشده")
            return
        insert_tasks(names)
        show_popup("تسک‌های شما ثبت شد")
        self.refresh_tasks()

    def refresh_tasks(self):
        tasks = get_tasks()
        container = self.ids.time_inputs_container
        container.clear_widgets()
        self.time_inputs_map = {}

        for tid, name in tasks:
            row = BoxLayout(size_hint_y=None, height=40, spacing=10)
            lbl = Label(text=f"{name} :", halign="right", valign="middle")
            lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
            ti = TextInput(hint_text="HH:MM (مثلا 25:30)", size_hint_x=0.4,
                           multiline=False, halign="right")
            row.add_widget(lbl)
            row.add_widget(ti)
            container.add_widget(row)
            self.time_inputs_map[tid] = ti

        self.ids.report_labels.text = "برای گرفتن گزارش، بازه تاریخ را وارد کن"

    def save_time_entries(self):
        tasks = get_tasks()
        if not tasks:
            show_popup("هیچ تسکی ثبت نشده")
            return

        date_j = self.ids.date_entry.text.strip()
        if not date_j:
            show_popup("تاریخ شمسی را وارد کن")
            return

        try:
            date_g = jalali_to_greg(date_j)
        except Exception as e:
            show_popup(str(e))
            return

        for tid, _ in tasks:
            ti = self.time_inputs_map.get(tid)
            if not ti:
                continue
            time_str = ti.text.strip()
            if not time_str:
                continue
            try:
                minutes = validate_time_to_minutes(time_str)
                insert_entry(tid, minutes, date_g, date_j)
            except Exception as e:
                show_popup(str(e))
                return

        show_popup("زمان‌ها ثبت شد")

    def generate_report(self):
        date_from_j = self.ids.date_from.text.strip()
        date_to_j = self.ids.date_to.text.strip()

        if not date_from_j or not date_to_j:
            show_popup("بازه تاریخ را کامل وارد کن")
            return

        try:
            date_from_g = jalali_to_greg(date_from_j)
            date_to_g = jalali_to_greg(date_to_j)
        except Exception as e:
            show_popup(str(e))
            return

        stats = get_stats_between(date_from_g, date_to_g)

        if not stats:
            self.ids.report_labels.text = "در این بازه داده‌ای ثبت نشده"
            self.ids.bar_chart.labels = []
            self.ids.bar_chart.values = []
            return

        labels = [s[0] for s in stats]
        values = [s[1] for s in stats]

        lines = []
        for name, total_min in stats:
            h = total_min // 60
            m = total_min % 60
            lines.append(f"{name} : {h:02}:{m:02}")
        self.ids.report_labels.text = "\n".join(lines)

        self.ids.bar_chart.labels = labels
        self.ids.bar_chart.values = values

class AshbahSiahApp(App):
    def build(self):
        init_db()
        self.title = "اشباح سیاه"
        return MainUI()

if __name__ == "__main__":
    AshbahSiahApp().run()
