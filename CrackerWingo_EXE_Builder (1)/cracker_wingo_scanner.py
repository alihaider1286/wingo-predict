import sys
import re
import csv
from pathlib import Path
from datetime import datetime
from collections import Counter

import mss
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox,
    QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QSpinBox
)

APP = Path.home() / "Documents" / "CrackerWingoScanner"
APP.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = APP / "history.csv"
CHART_FILE = APP / "chart_ocr_log.txt"


def colour_for(n):
    if n in (0, 5):
        return "Violet"
    if n in (1, 3, 7, 9):
        return "Green"
    return "Red"


def size_for(n):
    return "Small" if n <= 4 else "Big"


class AreaPicker(QWidget):

    def __init__(self, callback, prompt):
        super().__init__()

        self.callback = callback
        self.prompt = prompt
        self.start = QPoint()
        self.selection = QRect()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setWindowOpacity(0.22)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        p.setPen(QPen(QColor(0, 255, 130), 3))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        p.drawText(
            35, 55,
            self.prompt + " - drag to select, ESC to cancel"
        )

        if not self.selection.isNull():
            p.drawRect(self.selection)

    def mousePressEvent(self, e):
        self.start = e.position().toPoint()
        self.selection = QRect(self.start, self.start)
        self.update()

    def mouseMoveEvent(self, e):
        self.selection = QRect(
            self.start,
            e.position().toPoint()
        ).normalized()
        self.update()

    def mouseReleaseEvent(self, e):
        r = QRect(
            self.start,
            e.position().toPoint()
        ).normalized()

        self.callback(r)
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()


class Scanner(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("CRACKER Wingo Scanner")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setMinimumWidth(560)

        self.history_region = None
        self.chart_region = None
        self.rows = {}

        self.build_ui()
        self.load_history()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_scan)

        self.refresh_table()
        self.refresh_stats()

    def build_ui(self):

        self.setStyleSheet("""
        QWidget {
            background:#111827;
            color:#e5e7eb;
            font-family:Segoe UI;
        }

        QPushButton {
            background:#334155;
            color:white;
            padding:8px;
            border-radius:7px;
        }

        QTableWidget, QTextEdit {
            background:#0b1220;
            color:white;
        }
        """)

        outer = QVBoxLayout(self)

        header = QLabel("CRACKER WINGO SCANNER")
        header.setFont(
            QFont("Segoe UI", 15, QFont.Weight.Bold)
        )
        outer.addWidget(header)

        self.status = QLabel(
            "Ready. Open B9.Game Win Go and select History."
        )
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        top = QHBoxLayout()

        self.pick_history = QPushButton(
            "1. Select HISTORY area"
        )
        self.pick_history.clicked.connect(
            self.select_history
        )
        top.addWidget(self.pick_history)

        self.capture_history = QPushButton(
            "Capture history now"
        )
        self.capture_history.clicked.connect(
            self.scan_history
        )
        top.addWidget(self.capture_history)

        outer.addLayout(top)

        second = QHBoxLayout()

        self.pick_chart = QPushButton(
            "2. Select CHART area"
        )
        self.pick_chart.clicked.connect(
            self.select_chart
        )
        second.addWidget(self.pick_chart)

        self.capture_chart = QPushButton(
            "Capture chart / statistics"
        )
        self.capture_chart.clicked.connect(
            self.scan_chart
        )
        second.addWidget(self.capture_chart)

        outer.addLayout(second)

        controls = QHBoxLayout()

        self.auto_btn = QPushButton(
            "Start auto-monitor"
        )
        self.auto_btn.clicked.connect(
            self.toggle_auto
        )
        controls.addWidget(self.auto_btn)

        controls.addWidget(QLabel("Every (sec):"))

        self.interval = QSpinBox()
        self.interval.setRange(3, 30)
        self.interval.setValue(5)
        controls.addWidget(self.interval)

        self.next_btn = QPushButton(
            "Next page - scan again"
        )
        self.next_btn.clicked.connect(
            self.scan_history
        )
        controls.addWidget(self.next_btn)

        outer.addLayout(controls)

        self.tabs = QTabWidget()

        hist_tab = QWidget()
        hl = QVBoxLayout(hist_tab)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Period ID",
            "Number",
            "Big/Small",
            "Colour",
            "Source"
        ])

        self.table.horizontalHeader().setStretchLastSection(
            True
        )
        hl.addWidget(self.table)

        self.tabs.addTab(hist_tab, "History")

        stats_tab = QWidget()
        sl = QVBoxLayout(stats_tab)

        self.stats = QLabel("No history scanned yet.")
        self.stats.setWordWrap(True)
        sl.addWidget(self.stats)

        self.tabs.addTab(stats_tab, "Analysis")

        chart_tab = QWidget()
        cl = QVBoxLayout(chart_tab)

        self.chart_text = QTextEdit()
        self.chart_text.setReadOnly(True)
        self.chart_text.setPlaceholderText(
            "Chart OCR results will appear here."
        )

        cl.addWidget(self.chart_text)
        self.tabs.addTab(chart_tab, "Chart OCR")

        outer.addWidget(self.tabs)

        self.resize(720, 650)

    def notify(self, title, body):
        QMessageBox.information(
            self, title, body
        )

    def select_history(self):
        self.hide()

        QTimer.singleShot(
            350,
            lambda: AreaPicker(
                self.set_history_region,
                "Select HISTORY table"
            )
        )

    def set_history_region(self, r):

        if r.width() < 100 or r.height() < 45:
            self.status.setText(
                "Selection too small. Select the full history table."
            )
        else:
            self.history_region = (
                r.x(), r.y(), r.width(), r.height()
            )

            self.status.setText(
                "History area saved. Capture history now."
            )

        self.show()

    def select_chart(self):
        self.hide()

        QTimer.singleShot(
            350,
            lambda: AreaPicker(
                self.set_chart_region,
                "Select CHART statistics area"
            )
        )

    def set_chart_region(self, r):

        if r.width() < 100 or r.height() < 45:
            self.status.setText(
                "Chart selection too small."
            )
        else:
            self.chart_region = (
                r.x(), r.y(), r.width(), r.height()
            )

            self.status.setText(
                "Chart area saved."
            )

        self.show()

    def capture(self, region):

        x, y, w, h = region

        with mss.mss() as sct:
            raw = sct.grab({
                "left": x,
                "top": y,
                "width": w,
                "height": h
            })

        im = Image.frombytes(
            "RGB", raw.size, raw.rgb
        )

        gray = ImageOps.autocontrast(
            im.convert("L")
        )

        gray = gray.resize((
            gray.width * 3,
            gray.height * 3
        ))

        gray = ImageEnhance.Contrast(
            gray
        ).enhance(1.8)

        return gray

    def ocr(self, image, psm=6):
        return pytesseract.image_to_string(
            image,
            config=f"--oem 3 --psm {psm}"
        )

    def scan_history(self):

        if not self.history_region:
            self.notify(
                "Select history area",
                "Select the visible Game History table first."
            )
            return

        try:
            text = self.ocr(
                self.capture(self.history_region),
                6
            )

            added = self.parse_history(text)

            self.save_history()
            self.refresh_table()
            self.refresh_stats()

            if added:
                self.status.setText(
                    f"{added} new periods added. "
                    f"Total stored: {len(self.rows)}"
                )
            else:
                self.status.setText(
                    "No new periods detected. "
                    "Open older history rows and scan again."
                )

        except Exception as e:
            self.notify(
                "History OCR error",
                str(e)
            )

    def parse_history(self, text):

        added = 0

        for line in text.splitlines():

            m = re.search(
                r'(\d{10,})\D{0,35}([0-9])(?:\D|$)',
                line
            )

            if not m:
                continue

            period = m.group(1)
            digit = int(m.group(2))

            if period not in self.rows:

                self.rows[period] = {
                    "number": digit,
                    "source": "OCR",
                    "captured": datetime.now().isoformat(
                        timespec="seconds"
                    )
                }

                added += 1

        return added

    def load_history(self):

        if HISTORY_FILE.exists():

            try:
                with HISTORY_FILE.open(
                    newline="",
                    encoding="utf-8"
                ) as f:

                    for r in csv.DictReader(f):

                        self.rows[r["period"]] = {
                            "number": int(r["number"]),
                            "source": r.get("source", "CSV"),
                            "captured": r.get("captured", "")
                        }

            except Exception:
                pass

    def save_history(self):

        with HISTORY_FILE.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            w = csv.writer(f)

            w.writerow([
                "period",
                "number",
                "big_small",
                "colour",
                "source",
                "captured"
            ])

            for p, obj in sorted(
                self.rows.items(),
                reverse=True
            ):

                n = obj["number"]

                w.writerow([
                    p,
                    n,
                    size_for(n),
                    colour_for(n),
                    obj.get("source", "OCR"),
                    obj.get("captured", "")
                ])

    def refresh_table(self):

        items = sorted(
            self.rows.items(),
            reverse=True
        )

        self.table.setRowCount(
            min(250, len(items))
        )

        for r, (p, obj) in enumerate(items[:250]):

            n = obj["number"]

            vals = [
                p,
                str(n),
                size_for(n),
                colour_for(n),
                obj.get("source", "OCR")
            ]

            for c, v in enumerate(vals):
                self.table.setItem(
                    r, c, QTableWidgetItem(v)
                )

    def refresh_stats(self):

        items = sorted(
            self.rows.items(),
            key=lambda x: x[0]
        )

        nums = [
            o["number"] for _, o in items
        ]

        if not nums:
            self.stats.setText(
                "No history scanned yet."
            )
            return

        counts = Counter(nums)

        big = sum(n >= 5 for n in nums)
        small = len(nums) - big

        colors = Counter(
            colour_for(n) for n in nums
        )

        transitions = Counter(
            zip(nums, nums[1:])
        )

        seqs = Counter(
            tuple(nums[i:i + 3])
            for i in range(max(0, len(nums) - 2))
        )

        repeats = [
            (s, c)
            for s, c in seqs.items()
            if c > 1
        ]

        latest = ", ".join(
            str(n) for n in nums[-20:]
        )

        txt = (
            f"Stored rounds: {len(nums)}\n"
            f"Big: {big} | Small: {small}\n"
            f"Green: {colors['Green']} | "
            f"Red: {colors['Red']} | "
            f"Violet: {colors['Violet']}\n"
            f"Digit counts: "
            + " | ".join(
                f"{i}:{counts[i]}" for i in range(10)
            )
            + f"\nMost common transitions: "
            f"{transitions.most_common(5)}"
            f"\nRepeated 3-digit sequences: "
            f"{len(repeats)}"
            f"\nLatest 20 digits: {latest}"
            "\n\nHistorical repetition does not prove "
            "the next independent RNG result."
        )

        self.stats.setText(txt)

    def scan_chart(self):

        if not self.chart_region:

            self.tabs.setCurrentIndex(2)

            self.notify(
                "Open Chart first",
                "Open the Win Go Chart page, select its "
                "statistics area, then capture it."
            )
            return

        try:
            text = self.ocr(
                self.capture(self.chart_region),
                6
            )

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            with CHART_FILE.open(
                "a",
                encoding="utf-8"
            ) as f:

                f.write(
                    f"\n===== {timestamp} =====\n"
                )
                f.write(text + "\n")

            self.chart_text.setPlainText(
                text + "\n\nSaved to " + str(CHART_FILE)
            )

            self.tabs.setCurrentIndex(2)

            self.status.setText(
                "Chart OCR captured. Verify the recognized text."
            )

        except Exception as e:
            self.notify(
                "Chart OCR error",
                str(e)
            )

    def auto_scan(self):
        self.scan_history()

    def toggle_auto(self):

        if not self.history_region:

            self.notify(
                "Select history area first",
                "Select the Game History table before "
                "starting auto-monitor."
            )
            return

        if self.timer.isActive():

            self.timer.stop()
            self.auto_btn.setText(
                "Start auto-monitor"
            )
            self.status.setText(
                "Auto-monitor paused."
            )

        else:

            self.timer.start(
                self.interval.value() * 1000
            )

            self.auto_btn.setText(
                "Pause auto-monitor"
            )

            self.status.setText(
                "Auto-monitor running."
            )

            self.scan_history()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    win = Scanner()
    win.show()

    sys.exit(app.exec())
