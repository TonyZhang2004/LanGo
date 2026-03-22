import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib import error

from backend.language_state import language_options
from hardware.detection_client import (
    SERVER_BASE,
    confirm_pending,
    get_history,
    get_selected_language,
    get_selected_mode,
    list_pending,
    reject_pending,
    set_selected_language,
    set_selected_mode,
)

try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError:
    tk = None
    ttk = None


ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
OBJECT_DETECTION_SCRIPT = ROOT_DIR / "object-detection.py"
DEFAULT_POLL_MS = int(os.environ.get("LANGO_PI_POLL_MS", "2000"))
DEFAULT_WINDOW_MODE = os.environ.get("LANGO_PI_WINDOW_MODE", "fullscreen").strip().lower() or "fullscreen"
DETECTOR_AUTOSTART_ENABLED = os.environ.get("LANGO_DISABLE_DETECTOR_AUTOSTART", "").strip().lower() not in {
    "1",
    "true",
    "yes",
}

THEME = {
    "paper": "#f7f3eb",
    "paper_strong": "#fffdf9",
    "ink": "#151719",
    "muted": "#5c645f",
    "line": "#d1c2b4",
    "accent": "#6a4128",
    "accent_strong": "#4d2c18",
    "accent_soft": "#e8d5c2",
    "warm": "#c9986b",
    "surface": "#fbf2e6",
    "surface_alt": "#efe1d1",
    "danger": "#8e3b31",
    "success": "#6a4128",
}

TITLE_FONT = ("Avenir Next Condensed", 34, "bold")
SCREEN_PROFILE = {
    "width": 480,
    "height": 320,
    "shell_padding": 8,
    "stage_padding": 8,
    "stage_radius": 24,
    "panel_padding": 10,
    "panel_radius": 20,
    "header_gap": 6,
    "content_gap": 8,
    "status_wrap": 320,
}

BODY_FONT = ("Avenir Next", 13)
BODY_BOLD_FONT = ("Avenir Next", 13, "bold")
META_FONT = ("Avenir Next", 9, "bold")
DISPLAY_FONT = ("Avenir Next", 18)
DISPLAY_BOLD_FONT = ("Avenir Next", 22, "bold")
TOUCH_FONT = ("Avenir Next", 20, "bold")
TOUCH_FONT_SMALL = ("Avenir Next", 18, "bold")
CHIP_TITLE_FONT = ("Avenir Next", 16, "bold")
CHIP_SUBTITLE_FONT = ("Avenir Next", 11)
GEAR_ICON = "\u2699"
HOME_ICON = "\u2302"
SWITCHER_BAR_RELWIDTH = 0.84
SWITCHER_BAR_HEIGHT = 68
SWITCHER_BUTTON_WIDTH = 124
SWITCHER_BUTTON_HEIGHT = 52
MODE_TILE_SIZE = 124
MAX_HOME_PENDING = 1
QUEUE_GRID_COLUMNS = 1
QUEUE_CARD_HEIGHT = 154
QUEUE_ACTION_HEIGHT = 62
QUEUE_NAV_BUTTON_WIDTH = 56
QUEUE_NAV_BUTTON_HEIGHT = 36
NAV_BUTTON_SIZE = 42
SMALL_STATUS_MAX_CHARS = 30
SMALL_LABEL_MAX_CHARS = 18
SMALL_TRANSLATION_MAX_CHARS = 20


if tk is not None:
    class RoundedPanel(tk.Canvas):
        def __init__(self, parent, *, fill, border, radius=32, padding=0, **kwargs):
            super().__init__(
                parent,
                bg=parent.cget("bg"),
                highlightthickness=0,
                bd=0,
                relief="flat",
                **kwargs,
            )
            self.fill = fill
            self.border = border
            self.radius = radius
            self.padding = padding
            self.content = tk.Frame(self, bg=fill)
            self._content_window = self.create_window((padding, padding), window=self.content, anchor="nw")
            self.bind("<Configure>", self._redraw)

        def _rounded_points(self, width, height):
            radius = max(8, min(self.radius, width // 2, height // 2))
            x1 = y1 = 1
            x2 = max(x1 + 2, width - 1)
            y2 = max(y1 + 2, height - 1)
            return [
                x1 + radius,
                y1,
                x1 + radius,
                y1,
                x2 - radius,
                y1,
                x2 - radius,
                y1,
                x2,
                y1,
                x2,
                y1 + radius,
                x2,
                y1 + radius,
                x2,
                y2 - radius,
                x2,
                y2 - radius,
                x2,
                y2,
                x2 - radius,
                y2,
                x2 - radius,
                y2,
                x1 + radius,
                y2,
                x1 + radius,
                y2,
                x1,
                y2,
                x1,
                y2 - radius,
                x1,
                y2 - radius,
                x1,
                y1 + radius,
                x1,
                y1 + radius,
                x1,
                y1,
            ]

        def _redraw(self, _event=None):
            width = max(2, self.winfo_width())
            height = max(2, self.winfo_height())
            self.delete("panel-bg")
            self.create_polygon(
                self._rounded_points(width, height),
                smooth=True,
                splinesteps=36,
                fill=self.fill,
                outline=self.border,
                width=1,
                tags="panel-bg",
            )
            self.tag_lower("panel-bg")
            inset = self.padding
            self.coords(self._content_window, inset, inset)
            self.itemconfigure(
                self._content_window,
                width=max(1, width - (inset * 2)),
                height=max(1, height - (inset * 2)),
            )


    class RoundedButton(tk.Canvas):
        def __init__(
            self,
            parent,
            *,
            text,
            command,
            width,
            height,
            radius,
            fill,
            text_color,
            font,
            border,
            active_fill=None,
            disabled=False,
            subtitle=None,
            subtitle_font=CHIP_SUBTITLE_FONT,
            subtitle_color=None,
            pressed_fill=None,
        ):
            super().__init__(
                parent,
                width=width,
                height=height,
                bg=parent.cget("bg"),
                highlightthickness=0,
                bd=0,
                relief="flat",
                cursor="hand2" if not disabled else "arrow",
            )
            self.label = text
            self.command = command
            self.radius = radius
            self.fill = fill
            self.text_color = text_color
            self.font = font
            self.border = border
            self.active_fill = active_fill or fill
            self.pressed_fill = pressed_fill or self.active_fill
            self.disabled = disabled
            self.subtitle = subtitle
            self.subtitle_font = subtitle_font
            self.subtitle_color = subtitle_color or text_color
            self.is_hovered = False
            self.is_pressed = False
            self.bind("<Configure>", self._redraw)
            self.bind("<Enter>", self._handle_enter)
            self.bind("<Leave>", self._handle_leave)
            self.bind("<ButtonPress-1>", self._handle_press)
            self.bind("<ButtonRelease-1>", self._handle_release)
            self._redraw()

        def _rounded_points(self, width, height):
            radius = max(8, min(self.radius, width // 2, height // 2))
            x1 = y1 = 1
            x2 = max(x1 + 2, width - 1)
            y2 = max(y1 + 2, height - 1)
            return [
                x1 + radius,
                y1,
                x1 + radius,
                y1,
                x2 - radius,
                y1,
                x2 - radius,
                y1,
                x2,
                y1,
                x2,
                y1 + radius,
                x2,
                y1 + radius,
                x2,
                y2 - radius,
                x2,
                y2 - radius,
                x2,
                y2,
                x2 - radius,
                y2,
                x2 - radius,
                y2,
                x1 + radius,
                y2,
                x1 + radius,
                y2,
                x1,
                y2,
                x1,
                y2 - radius,
                x1,
                y2 - radius,
                x1,
                y1 + radius,
                x1,
                y1 + radius,
                x1,
                y1,
            ]

        def _current_fill(self):
            if self.disabled:
                return THEME["accent_soft"]
            if self.is_pressed:
                return self.pressed_fill
            if self.is_hovered:
                return self.active_fill
            return self.fill

        def _redraw(self, _event=None):
            width = max(2, self.winfo_width())
            height = max(2, self.winfo_height())
            fill = self._current_fill()
            self.delete("button")
            self.create_polygon(
                self._rounded_points(width, height),
                smooth=True,
                splinesteps=36,
                fill=fill,
                outline=self.border,
                width=1,
                tags="button",
            )
            if self.subtitle:
                self.create_text(
                    width / 2,
                    height * 0.38,
                    text=self.label,
                    fill=self.text_color,
                    font=self.font,
                    tags="button",
                )
                self.create_text(
                    width / 2,
                    height * 0.68,
                    text=self.subtitle,
                    fill=self.subtitle_color,
                    font=self.subtitle_font,
                    tags="button",
                )
            else:
                self.create_text(
                    width / 2,
                    height / 2,
                    text=self.label,
                    fill=self.text_color,
                    font=self.font,
                    tags="button",
                )

        def _handle_enter(self, _event):
            if self.disabled:
                return
            self.is_hovered = True
            self._redraw()

        def _handle_leave(self, _event):
            self.is_hovered = False
            self.is_pressed = False
            self._redraw()

        def _handle_press(self, _event):
            if self.disabled:
                return
            self.is_pressed = True
            self._redraw()

        def _handle_release(self, event):
            if self.disabled:
                return
            was_pressed = self.is_pressed
            self.is_pressed = False
            self._redraw()
            if was_pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
                self.command()
else:
    class RoundedPanel:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("Tkinter is not available in this Python environment.")


    class RoundedButton:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("Tkinter is not available in this Python environment.")


def format_display_time(timestamp, fallback_time=""):
    if timestamp:
        normalized = str(timestamp).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            hour = parsed.strftime("%I").lstrip("0") or "0"
            return f"{parsed.strftime('%B')} {parsed.day}, {hour}:{parsed.strftime('%M %p')}"
        except ValueError:
            pass
    if fallback_time:
        today = datetime.now()
        return f"{today.strftime('%B')} {today.day}, {fallback_time}"
    return "Unknown time"


def choose_selected_pending_id(pending_items, current_id):
    pending_ids = [item.get("pendingId") for item in pending_items]
    if current_id in pending_ids:
        return current_id
    return pending_ids[0] if pending_ids else None


def truncate_copy(text, max_chars):
    value = " ".join(str(text or "").split())
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    if max_chars == 1:
        return "\u2026"
    return value[: max_chars - 1].rstrip() + "\u2026"


def compact_language_label(label):
    value = " ".join(str(label or "").split())
    if value == "Mandarin Chinese":
        return "Mandarin"
    return value


def queue_position_label(pending_items, selected_id):
    if not pending_items:
        return "0 of 0"

    pending_ids = [item.get("pendingId") for item in pending_items]
    if selected_id in pending_ids:
        return f"{pending_ids.index(selected_id) + 1}/{len(pending_ids)}"
    return f"1/{len(pending_ids)}"


def format_queue_status(language_label, pending_count, max_chars=SMALL_STATUS_MAX_CHARS):
    compact_label = truncate_copy(language_label, max_chars)
    return f"{compact_label} \u00b7 {pending_count} waiting"


def should_show_queue_navigation(pending_items):
    return len(pending_items) > 1


def resolve_window_mode(window_mode=None):
    normalized = str(window_mode or DEFAULT_WINDOW_MODE).strip().lower()
    if normalized not in {"fullscreen", "windowed"}:
        return "fullscreen"
    return normalized


def resolve_supported_image(image_path):
    if not image_path:
        return None
    relative = str(image_path).removeprefix("./")
    file_path = FRONTEND_DIR / relative
    if not file_path.exists():
        return None
    if file_path.suffix.lower() not in {".png", ".gif", ".ppm", ".pgm"}:
        return None
    return file_path


def format_main_message(mode_key, selected_pending, latest_entry):
    if mode_key == "game":
        return "game mode coming soon"
    if selected_pending:
        return f"{selected_pending.get('english', '')} \u2192 {selected_pending.get('translated', '')}"
    if latest_entry:
        return f"{latest_entry.get('english', '')} \u2192 {latest_entry.get('translated', '')}"
    return "point to start translating"


def navigation_icon(show_settings):
    return HOME_ICON if show_settings else GEAR_ICON


def visible_pending_items(pending_items, max_items=MAX_HOME_PENDING):
    return list(pending_items[:max_items])


def format_pending_label(pending):
    english = str(pending.get("english", "")).strip()
    translated = str(pending.get("translated", "")).strip()
    if english and translated:
        return f"{english} \u2192 {translated}"
    return english or translated or "Pending translation"


def selected_pending_item(pending_items, selected_id):
    for item in pending_items:
        if item.get("pendingId") == selected_id:
            return item
    return pending_items[0] if pending_items else None


class LanGoPiApp:
    def __init__(self, root=None, server_base=SERVER_BASE, poll_ms=DEFAULT_POLL_MS, window_mode=None):
        if tk is None or ttk is None:
            raise RuntimeError("Tkinter is not available in this Python environment.")
        self.root = root or tk.Tk()
        self.server_base = server_base
        self.poll_ms = poll_ms
        self.window_mode = resolve_window_mode(window_mode)
        self.languages = language_options()
        self.selected_language = {"key": "spanish", "label": "Spanish", "locale": "es-ES"}
        self.pending_items = []
        self.history_entries = []
        self.selected_pending_id = None
        self.settings_tab = "language"
        self.current_mode = "learn"
        self.show_settings = False
        self.status_message = "Connecting to LanGo..."
        self.status_tone = "muted"
        self.image_cache = {}
        self.poll_job = None
        self.detector_process = None

        self.shell = None
        self.status_label = None
        self.content_frame = None

        self._configure_root()
        self._configure_style()
        self._build_shell()
        self._initialize_runtime_mode()
        self._ensure_detector_running()
        self._refresh_data()

    def _data_signature(self):
        pending_signature = tuple(
            (
                item.get("pendingId"),
                item.get("english"),
                item.get("translated"),
                item.get("image"),
                item.get("createdAt"),
            )
            for item in self.pending_items
        )
        history_signature = tuple(
            (
                item.get("id"),
                item.get("english"),
                item.get("translated"),
                item.get("image"),
                item.get("createdAt"),
            )
            for item in self.history_entries[:1]
        )
        language_signature = tuple(
            (item.get("key"), item.get("label"), item.get("locale"))
            for item in self.languages
        )
        return (
            self.selected_language.get("key"),
            self.current_mode,
            self.selected_pending_id,
            language_signature,
            pending_signature,
            history_signature,
        )

    def _configure_root(self):
        self.root.title("LanGo Pi")
        self.root.minsize(SCREEN_PROFILE["width"], SCREEN_PROFILE["height"])
        self.root.configure(bg=THEME["paper"])
        self.root.bind("<Tab>", self._exit_fullscreen)
        if self.window_mode == "windowed":
            self.root.attributes("-fullscreen", False)
            self.root.geometry(f"{SCREEN_PROFILE['width']}x{SCREEN_PROFILE['height']}")
            self.root.resizable(False, False)
        else:
            self.root.attributes("-fullscreen", True)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "LanGo.Horizontal.TScrollbar",
            troughcolor=THEME["paper"],
            background=THEME["surface_alt"],
            bordercolor=THEME["line"],
            arrowcolor=THEME["ink"],
        )
        style.configure(
            "LanGo.Vertical.TScrollbar",
            troughcolor=THEME["paper"],
            background=THEME["surface_alt"],
            bordercolor=THEME["line"],
            arrowcolor=THEME["ink"],
        )

    def run(self):
        self.root.mainloop()

    def _handle_close(self):
        self._cancel_poll()
        self._stop_detector_process()
        self.root.destroy()

    def _exit_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", False)

    def _cancel_poll(self):
        if self.poll_job:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None

    def _schedule_refresh(self):
        self._cancel_poll()
        self.poll_job = self.root.after(self.poll_ms, self._refresh_data)

    def _initialize_runtime_mode(self):
        self.current_mode = "learn"
        try:
            _, payload = set_selected_mode("learn", server_base=self.server_base)
            self.current_mode = payload.get("selectedMode", "learn")
        except Exception:
            self.current_mode = "learn"

    def _ensure_detector_running(self):
        if not DETECTOR_AUTOSTART_ENABLED:
            return
        if self.detector_process and self.detector_process.poll() is None:
            return

        env = os.environ.copy()
        env.setdefault("LANGO_SERVER_BASE", self.server_base)
        try:
            self.detector_process = subprocess.Popen(
                [sys.executable, str(OBJECT_DETECTION_SCRIPT)],
                cwd=str(ROOT_DIR),
                env=env,
            )
        except Exception as exc:
            self.detector_process = None
            self._set_status(f"Could not start detector: {exc}", "error")

    def _stop_detector_process(self):
        if not self.detector_process:
            return
        if self.detector_process.poll() is None:
            self.detector_process.terminate()
            try:
                self.detector_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.detector_process.kill()
                self.detector_process.wait(timeout=5)
        self.detector_process = None

    def _build_shell(self):
        for child in self.root.winfo_children():
            child.destroy()

        self.shell = tk.Frame(self.root, bg=THEME["paper"])
        self.shell.pack(
            fill="both",
            expand=True,
            padx=SCREEN_PROFILE["shell_padding"],
            pady=SCREEN_PROFILE["shell_padding"],
        )

        self.status_label = tk.Label(
            self.shell,
            text=self.status_message,
            bg=THEME["paper"],
            fg=THEME["muted"],
            font=("Avenir Next", 11, "bold"),
            wraplength=SCREEN_PROFILE["status_wrap"],
            justify="left",
        )

        self.content_frame = tk.Frame(self.shell, bg=THEME["paper"])
        self.content_frame.pack(fill="both", expand=True)
        self._render_screen()

    def _render_screen(self):
        for child in self.content_frame.winfo_children():
            child.destroy()
        if self.show_settings:
            self._render_settings_screen()
        else:
            self._render_main_screen()

    def _render_main_screen(self):
        stage = self._make_stage(self.content_frame)
        stage.pack(fill="both", expand=True)
        surface = stage.content
        topbar = tk.Frame(surface, bg=THEME["paper_strong"])
        topbar.pack(fill="x", pady=(0, SCREEN_PROFILE["header_gap"]))
        tk.Label(
            topbar,
            text=truncate_copy(compact_language_label(self.selected_language["label"]), 14),
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=BODY_BOLD_FONT,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self._add_nav_button(topbar, navigation_icon(False)).pack(side="right")
        if self.current_mode == "game":
            game_panel = RoundedPanel(
                surface,
                fill=THEME["surface"],
                border=THEME["line"],
                radius=SCREEN_PROFILE["panel_radius"],
                padding=SCREEN_PROFILE["panel_padding"],
            )
            game_panel.pack(fill="both", expand=True)
            self._render_game_placeholder(game_panel.content)
            return

        queue_panel = RoundedPanel(
            surface,
            fill=THEME["surface"],
            border=THEME["line"],
            radius=SCREEN_PROFILE["panel_radius"],
            padding=SCREEN_PROFILE["panel_padding"],
        )
        queue_panel.pack(fill="both", expand=True)
        self._render_pending_queue(queue_panel.content)

    def _render_game_placeholder(self, parent):
        tk.Label(
            parent,
            text="Game",
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            parent,
            text="Game mode is visible here, but still not functional on Raspberry Pi.",
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            font=BODY_FONT,
            wraplength=SCREEN_PROFILE["width"] - 80,
            justify="left",
        ).pack(anchor="w")

    def _render_pending_queue(self, parent):
        if not self.pending_items:
            tk.Label(
                parent,
                text="No pending detections.",
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=BODY_FONT,
                justify="center",
                wraplength=SCREEN_PROFILE["width"] - 80,
            ).pack(anchor="center", expand=True)
            return

        selected_item = selected_pending_item(self.pending_items, self.selected_pending_id)
        self._render_pending_card(parent, selected_item)

        if should_show_queue_navigation(self.pending_items):
            controls = tk.Frame(parent, bg=THEME["surface"])
            controls.pack(fill="x", pady=(SCREEN_PROFILE["content_gap"], 0))
            controls.grid_columnconfigure(1, weight=1)

            self._make_queue_nav_button(controls, "\u2039", -1).grid(row=0, column=0, sticky="w")
            tk.Label(
                controls,
                text=queue_position_label(self.pending_items, selected_item.get("pendingId")),
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=META_FONT,
                anchor="center",
            ).grid(row=0, column=1, sticky="nsew")
            self._make_queue_nav_button(controls, "\u203a", 1).grid(row=0, column=2, sticky="e")

    def _render_pending_card(self, parent, pending):
        card = RoundedPanel(
            parent,
            fill=THEME["paper_strong"],
            border=THEME["line"],
            radius=SCREEN_PROFILE["panel_radius"],
            padding=SCREEN_PROFILE["panel_padding"],
            height=QUEUE_CARD_HEIGHT,
        )
        card.pack(fill="both", expand=True)
        body = card.content
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1, uniform="pending-action")
        body.grid_columnconfigure(1, weight=1, uniform="pending-action")

        summary = tk.Frame(body, bg=THEME["paper_strong"])
        summary.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            summary,
            text=truncate_copy(pending.get("english", ""), SMALL_LABEL_MAX_CHARS),
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            font=DISPLAY_BOLD_FONT,
            anchor="center",
            justify="center",
        ).pack(fill="x")
        tk.Label(
            summary,
            text=truncate_copy(pending.get("translated", ""), SMALL_TRANSLATION_MAX_CHARS),
            bg=THEME["paper_strong"],
            fg=THEME["accent_strong"],
            font=DISPLAY_FONT,
            anchor="center",
            justify="center",
        ).pack(fill="x", pady=(8, 0))

        RoundedButton(
            body,
            text="Save",
            command=lambda item=pending: self._confirm_pending_item(item),
            width=132,
            height=QUEUE_ACTION_HEIGHT,
            radius=22,
            fill=THEME["accent"],
            active_fill=THEME["accent_strong"],
            pressed_fill=THEME["accent_strong"],
            text_color=THEME["paper_strong"],
            font=TOUCH_FONT_SMALL,
            border=THEME["line"],
        ).grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(14, 0))
        RoundedButton(
            body,
            text="Discard",
            command=lambda item=pending: self._reject_pending_item(item),
            width=132,
            height=QUEUE_ACTION_HEIGHT,
            radius=22,
            fill=THEME["warm"],
            active_fill=THEME["accent_soft"],
            pressed_fill=THEME["accent_strong"],
            text_color=THEME["accent_strong"],
            font=TOUCH_FONT_SMALL,
            border=THEME["line"],
        ).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(14, 0))

    def _render_settings_screen(self):
        stage = self._make_stage(self.content_frame)
        stage.pack(fill="both", expand=True)
        surface = stage.content
        header = tk.Frame(surface, bg=THEME["paper_strong"])
        header.pack(fill="x", pady=(0, SCREEN_PROFILE["header_gap"]))
        title_block = tk.Frame(header, bg=THEME["paper_strong"])
        title_block.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_block,
            text="Settings",
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            font=DISPLAY_BOLD_FONT,
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text="Language and mode",
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=META_FONT,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        self._add_nav_button(header, navigation_icon(True)).pack(side="right")

        slider = RoundedPanel(
            surface,
            fill=THEME["surface_alt"],
            border=THEME["line"],
            radius=22,
            padding=6,
            height=SWITCHER_BAR_HEIGHT,
        )
        slider.pack(fill="x", pady=(0, SCREEN_PROFILE["content_gap"]))

        slider.content.configure(bg=THEME["surface_alt"])
        slider.content.grid_columnconfigure(0, weight=1, uniform="settings-switch")
        slider.content.grid_columnconfigure(1, weight=1, uniform="settings-switch")
        slider.content.grid_rowconfigure(0, weight=1)
        self._make_slider_button(slider.content, "Language", "language").grid(
            row=0,
            column=0,
            padx=(0, 8),
            sticky="nsew",
        )
        self._make_slider_button(slider.content, "Mode", "mode").grid(
            row=0,
            column=1,
            padx=(8, 0),
            sticky="nsew",
        )

        settings_card = RoundedPanel(
            surface,
            fill=THEME["paper_strong"],
            border=THEME["line"],
            radius=SCREEN_PROFILE["panel_radius"],
            padding=SCREEN_PROFILE["panel_padding"],
        )
        settings_card.pack(fill="both", expand=True)

        title_text = "Language" if self.settings_tab == "language" else "Mode"
        tk.Label(
            settings_card.content,
            text=title_text,
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="w", pady=(0, 6))

        body_host = tk.Frame(settings_card.content, bg=THEME["paper_strong"])
        body_host.pack(fill="both", expand=True)

        if self.settings_tab == "language":
            self._render_language_buttons(body_host)
        else:
            self._render_mode_buttons(body_host)

    def _render_language_buttons(self, parent):
        if not self.languages:
            tk.Label(
                parent,
                text="No languages loaded yet.",
                bg=THEME["paper_strong"],
                fg=THEME["muted"],
                font=BODY_FONT,
            ).pack(anchor="center", expand=True)
            return

        grid = tk.Frame(parent, bg=THEME["paper_strong"])
        grid.pack(expand=True, fill="both", pady=(4, 0))
        columns = 2
        for index, language in enumerate(self.languages):
            row = index // columns
            column = index % columns
            is_selected = language["key"] == self.selected_language["key"]
            button = self._make_option_button(
                grid,
                truncate_copy(compact_language_label(language["label"]), 15),
                is_selected,
                lambda key=language["key"]: self._handle_language_change(key),
            )
            button.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
            grid.grid_columnconfigure(column, weight=1, uniform="language-column")
            grid.grid_rowconfigure(row, weight=1)

    def _render_mode_buttons(self, parent):
        wrap = tk.Frame(parent, bg=THEME["paper_strong"])
        wrap.pack(expand=True, fill="both", pady=(12, 0))

        mode_meta = (
            ("Learn", "learn", "Study words"),
            ("Game", "game", "Play mode"),
        )
        for index, (label, key, subtitle) in enumerate(mode_meta):
            is_selected = self.current_mode == key
            button = self._make_mode_tile(
                wrap,
                label,
                subtitle,
                is_selected,
                lambda value=key: self._switch_mode(value),
            )
            button.grid(row=0, column=index, padx=8, pady=8, sticky="nsew")
            wrap.grid_columnconfigure(index, weight=1, uniform="mode-column")
        wrap.grid_rowconfigure(0, weight=1)

    def _make_option_button(self, parent, text, is_selected, command):
        return RoundedButton(
            parent,
            text=text,
            command=command,
            width=146,
            height=72,
            radius=24,
            fill=THEME["accent"] if is_selected else THEME["surface_alt"],
            active_fill=THEME["accent_soft"] if is_selected else THEME["surface"],
            pressed_fill=THEME["accent_strong"] if is_selected else THEME["warm"],
            text_color=THEME["paper_strong"] if is_selected else THEME["ink"],
            font=TOUCH_FONT_SMALL,
            border=THEME["line"],
        )

    def _make_mode_tile(self, parent, text, subtitle, is_selected, command):
        return RoundedButton(
            parent,
            text=text,
            subtitle=subtitle,
            command=command,
            width=MODE_TILE_SIZE,
            height=MODE_TILE_SIZE,
            radius=28,
            fill=THEME["accent"] if is_selected else THEME["surface_alt"],
            active_fill=THEME["accent_soft"] if is_selected else THEME["surface"],
            pressed_fill=THEME["accent_strong"] if is_selected else THEME["warm"],
            text_color=THEME["paper_strong"] if is_selected else THEME["ink"],
            subtitle_color=THEME["paper"] if is_selected else THEME["muted"],
            font=TOUCH_FONT_SMALL,
            subtitle_font=("Avenir Next", 11, "bold"),
            border=THEME["line"],
        )

    def _make_slider_button(self, parent, text, tab_key):
        is_selected = self.settings_tab == tab_key
        return RoundedButton(
            parent,
            text=text,
            command=lambda: self._switch_settings_tab(tab_key),
            width=SWITCHER_BUTTON_WIDTH,
            height=SWITCHER_BUTTON_HEIGHT,
            radius=18,
            fill=THEME["accent"] if is_selected else THEME["surface_alt"],
            active_fill=THEME["accent_soft"] if is_selected else THEME["surface"],
            pressed_fill=THEME["accent_strong"] if is_selected else THEME["warm"],
            text_color=THEME["paper_strong"] if is_selected else THEME["ink"],
            font=TOUCH_FONT_SMALL,
            border=THEME["line"],
        )

    def _make_stage(self, parent):
        stage = RoundedPanel(
            parent,
            fill=THEME["paper_strong"],
            border=THEME["line"],
            radius=SCREEN_PROFILE["stage_radius"],
            padding=SCREEN_PROFILE["stage_padding"],
        )
        return stage

    def _add_nav_button(self, parent, icon_text):
        return RoundedButton(
            parent,
            text=icon_text,
            command=self._toggle_settings,
            width=NAV_BUTTON_SIZE,
            height=NAV_BUTTON_SIZE,
            radius=14,
            fill=THEME["surface"],
            active_fill=THEME["paper_strong"],
            pressed_fill=THEME["accent_soft"],
            text_color=THEME["ink"],
            font=("Avenir Next", 22),
            border=THEME["line"],
        )

    def _make_queue_nav_button(self, parent, text, direction):
        disabled = len(self.pending_items) <= 1
        return RoundedButton(
            parent,
            text=text,
            command=lambda step=direction: self._shift_selected_pending(step),
            width=QUEUE_NAV_BUTTON_WIDTH,
            height=QUEUE_NAV_BUTTON_HEIGHT,
            radius=18,
            fill=THEME["surface_alt"],
            active_fill=THEME["surface"],
            pressed_fill=THEME["accent_soft"],
            text_color=THEME["ink"],
            font=("Avenir Next", 24, "bold"),
            border=THEME["line"],
            disabled=disabled,
        )

    def _toggle_settings(self):
        self.show_settings = not self.show_settings
        self._render_screen()

    def _switch_settings_tab(self, tab_key):
        self.settings_tab = tab_key
        self._render_screen()

    def _switch_mode(self, mode_key):
        try:
            _, payload = set_selected_mode(mode_key, server_base=self.server_base)
            self.current_mode = payload.get("selectedMode", self.current_mode)
            self._set_status(f"{self.current_mode.title()} mode selected.", "success")
            self._render_screen()
        except Exception as exc:
            self._set_status(f"Could not switch mode: {exc}", "error")

    def _shift_selected_pending(self, direction):
        if len(self.pending_items) <= 1:
            return

        pending_ids = [item.get("pendingId") for item in self.pending_items]
        current_id = choose_selected_pending_id(self.pending_items, self.selected_pending_id)
        current_index = pending_ids.index(current_id)
        next_index = (current_index + direction) % len(pending_ids)
        self.selected_pending_id = pending_ids[next_index]
        self._render_screen()

    def _set_status(self, message, tone="muted"):
        self.status_message = message
        self.status_tone = tone
        if self.status_label:
            self.status_label.configure(text=message, fg=self._status_color(tone))

    def _status_color(self, tone):
        if tone == "error":
            return THEME["danger"]
        if tone == "success":
            return THEME["success"]
        return THEME["muted"]

    def _refresh_data(self, force_render=False):
        previous_signature = self._data_signature()
        self._ensure_detector_running()
        try:
            status_code, language_payload = get_selected_language(server_base=self.server_base)
            if status_code >= 400:
                raise error.HTTPError("", status_code, "language request failed", None, None)
            mode_status_code, mode_payload = get_selected_mode(server_base=self.server_base)
            if mode_status_code >= 400:
                raise error.HTTPError("", mode_status_code, "mode request failed", None, None)

            self.languages = language_payload.get("languages") or self.languages
            self.selected_language = language_payload.get("selectedLanguage", self.selected_language)
            self.current_mode = mode_payload.get("selectedMode", self.current_mode)
            language_key = self.selected_language["key"]

            _, pending_payload = list_pending(language_key=language_key, server_base=self.server_base)
            _, history_payload = get_history(language_key=language_key, server_base=self.server_base)

            self.pending_items = pending_payload.get("pending", [])
            self.history_entries = history_payload.get("entries", [])
            self.selected_pending_id = choose_selected_pending_id(self.pending_items, self.selected_pending_id)
            self._set_status(
                format_queue_status(self.selected_language["label"], len(self.pending_items)),
                "success",
            )
        except Exception as exc:
            self._set_status(f"Could not reach LanGo backend: {exc}", "error")
        finally:
            if force_render or self._data_signature() != previous_signature or not self.content_frame.winfo_children():
                self._render_screen()
            self._schedule_refresh()

    def _handle_language_change(self, language_key):
        try:
            _, payload = set_selected_language(language_key, server_base=self.server_base)
            self.selected_language = payload.get("selectedLanguage", self.selected_language)
            self.languages = payload.get("languages", self.languages)
            self._set_status(f"{self.selected_language['label']} is now active for new detections.", "success")
            self._refresh_data(force_render=True)
        except Exception as exc:
            self._set_status(f"Could not switch language: {exc}", "error")

    def _confirm_pending_item(self, pending):
        try:
            _, payload = confirm_pending(pending["pendingId"], server_base=self.server_base)
            entry = payload.get("entry", {})
            self._set_status(f"Saved {entry.get('english', pending.get('english', 'item'))} to history.", "success")
            self._refresh_data()
        except Exception as exc:
            self._set_status(f"Could not add item to history: {exc}", "error")

    def _reject_pending_item(self, pending):
        try:
            reject_pending(pending["pendingId"], server_base=self.server_base)
            self._set_status(f"Discarded {pending.get('english', 'item')}.", "success")
            self._refresh_data()
        except Exception as exc:
            self._set_status(f"Could not reject item: {exc}", "error")

    def _load_supported_photo(self, image_path, target_size):
        file_path = resolve_supported_image(image_path)
        if not file_path:
            return None
        cache_key = (str(file_path), target_size)
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        try:
            image = tk.PhotoImage(file=str(file_path))
        except tk.TclError:
            return None
        scale = max(1, max(image.width(), image.height()) // target_size)
        if scale > 1:
            image = image.subsample(scale, scale)
        self.image_cache[cache_key] = image
        return image


def main():
    app = LanGoPiApp()
    app.run()


if __name__ == "__main__":
    main()
