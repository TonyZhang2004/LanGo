import os
from datetime import datetime
from pathlib import Path
from urllib import error

from hardware.detection_client import (
    SERVER_BASE,
    confirm_pending,
    get_history,
    get_selected_language,
    list_pending,
    reject_pending,
    set_selected_language,
)

try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError:
    tk = None
    ttk = None


ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DEFAULT_POLL_MS = int(os.environ.get("LANGO_PI_POLL_MS", "2000"))

THEME = {
    "paper": "#f7f3eb",
    "paper_strong": "#fffdf9",
    "ink": "#151719",
    "muted": "#5c645f",
    "line": "#d8d3c7",
    "accent": "#d7ff5c",
    "accent_strong": "#9bde37",
    "accent_soft": "#edf8c8",
    "warm": "#f2b46b",
    "surface": "#fffaf1",
    "surface_alt": "#f4ede0",
    "danger": "#8e3b31",
    "success": "#4e7d20",
}

TITLE_FONT = ("Avenir Next Condensed", 42, "bold")
SECTION_FONT = ("Avenir Next Condensed", 28, "bold")
BODY_FONT = ("Avenir Next", 16)
BODY_BOLD_FONT = ("Avenir Next", 16, "bold")
META_FONT = ("Avenir Next", 10, "bold")
BUTTON_FONT = ("Avenir Next", 15, "bold")


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


class LanGoPiApp:
    def __init__(self, root=None, server_base=SERVER_BASE, poll_ms=DEFAULT_POLL_MS):
        if tk is None or ttk is None:
            raise RuntimeError("Tkinter is not available in this Python environment.")
        self.root = root or tk.Tk()
        self.server_base = server_base
        self.poll_ms = poll_ms
        self.languages = []
        self.selected_language = {"key": "spanish", "label": "Spanish", "locale": "es-ES"}
        self.pending_items = []
        self.history_entries = []
        self.selected_pending_id = None
        self.active_tab = "language"
        self.current_mode = "learn"
        self.status_message = "Connecting to LanGo..."
        self.status_tone = "muted"
        self.image_cache = {}
        self.poll_job = None

        self.status_label = None
        self.current_target_label = None
        self.updated_label = None
        self.content_frame = None

        self._configure_root()
        self._configure_style()
        self._build_start_screen()

    def _configure_root(self):
        self.root.title("LanGo Pi")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=THEME["paper"])
        self.root.bind("<Tab>", self._exit_fullscreen)

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

    def _exit_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", False)

    def _clear_root(self):
        self._cancel_poll()
        for child in self.root.winfo_children():
            child.destroy()

    def _build_start_screen(self):
        self._clear_root()

        shell = tk.Frame(self.root, bg=THEME["paper"])
        shell.pack(fill="both", expand=True, padx=36, pady=36)

        hero = tk.Frame(
            shell,
            bg=THEME["surface"],
            highlightbackground=THEME["line"],
            highlightthickness=1,
            padx=40,
            pady=40,
        )
        hero.pack(expand=True)

        tk.Label(
            hero,
            text="LANGUAGE COMPANION",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="w")
        tk.Label(
            hero,
            text="LanGo",
            bg=THEME["surface"],
            fg=THEME["ink"],
            font=TITLE_FONT,
        ).pack(anchor="w", pady=(12, 18))
        tk.Label(
            hero,
            text="Point to start translating.",
            bg=THEME["surface"],
            fg=THEME["ink"],
            font=("Avenir Next", 20),
        ).pack(anchor="w")
        tk.Label(
            hero,
            text="Use the Raspberry Pi screen to choose the language and manage detected words.",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=BODY_FONT,
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(8, 28))

        tk.Button(
            hero,
            text="Open LanGo",
            command=self._build_main_shell,
            bg=THEME["accent_soft"],
            fg=THEME["ink"],
            activebackground=THEME["accent"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=24,
            pady=14,
            font=BUTTON_FONT,
            cursor="hand2",
        ).pack(anchor="w")

    def _build_main_shell(self):
        self._clear_root()

        shell = tk.Frame(self.root, bg=THEME["paper"])
        shell.pack(fill="both", expand=True, padx=24, pady=24)

        header = tk.Frame(
            shell,
            bg=THEME["surface"],
            highlightbackground=THEME["line"],
            highlightthickness=1,
            padx=26,
            pady=20,
        )
        header.pack(fill="x")

        header_left = tk.Frame(header, bg=THEME["surface"])
        header_left.pack(side="left", anchor="n")

        tk.Label(
            header_left,
            text="LANGUAGE COMPANION",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="w")
        tk.Label(
            header_left,
            text="LanGo",
            bg=THEME["surface"],
            fg=THEME["ink"],
            font=("Avenir Next Condensed", 34, "bold"),
        ).pack(anchor="w")

        header_right = tk.Frame(header, bg=THEME["surface"])
        header_right.pack(side="right", anchor="n")

        tk.Label(
            header_right,
            text="CURRENT TARGET",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="e")
        self.current_target_label = tk.Label(
            header_right,
            text=self.selected_language["label"],
            bg=THEME["surface"],
            fg=THEME["ink"],
            font=("Avenir Next", 18, "bold"),
        )
        self.current_target_label.pack(anchor="e")
        self.updated_label = tk.Label(
            header_right,
            text="Not synced yet",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=("Avenir Next", 12),
        )
        self.updated_label.pack(anchor="e", pady=(8, 0))

        controls = tk.Frame(shell, bg=THEME["paper"])
        controls.pack(fill="x", pady=(18, 12))

        self._build_tab_button(controls, "Language", "language").pack(side="left", padx=(0, 10))
        self._build_tab_button(controls, "Mode", "mode").pack(side="left")
        tk.Button(
            controls,
            text="Sync now",
            command=self._refresh_data,
            bg=THEME["surface"],
            fg=THEME["ink"],
            activebackground=THEME["accent_soft"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=18,
            pady=10,
            font=BODY_BOLD_FONT,
            cursor="hand2",
        ).pack(side="right")

        self.status_label = tk.Label(
            shell,
            text=self.status_message,
            bg=THEME["paper"],
            fg=THEME["muted"],
            font=BODY_FONT,
        )
        self.status_label.pack(fill="x", anchor="w", pady=(0, 14))

        self.content_frame = tk.Frame(
            shell,
            bg=THEME["paper"],
        )
        self.content_frame.pack(fill="both", expand=True)

        self._render_content()
        self._refresh_data()

    def _build_tab_button(self, parent, label, tab_key):
        is_selected = self.active_tab == tab_key
        return tk.Button(
            parent,
            text=label,
            command=lambda: self._switch_tab(tab_key),
            bg=THEME["accent_soft"] if is_selected else THEME["surface"],
            fg=THEME["ink"],
            activebackground=THEME["accent"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=18,
            pady=10,
            font=BODY_BOLD_FONT,
            cursor="hand2",
        )

    def _switch_tab(self, tab_key):
        self.active_tab = tab_key
        self._build_main_shell()

    def _switch_mode(self, mode_key):
        self.current_mode = mode_key
        self._render_content()

    def _set_status(self, message, tone="muted"):
        self.status_message = message
        self.status_tone = tone
        if not self.status_label:
            return
        self.status_label.configure(text=message, fg=self._status_color(tone))

    def _status_color(self, tone):
        if tone == "error":
            return THEME["danger"]
        if tone == "success":
            return THEME["success"]
        return THEME["muted"]

    def _refresh_data(self):
        try:
            status_code, language_payload = get_selected_language(server_base=self.server_base)
            if status_code >= 400:
                raise error.HTTPError("", status_code, "language request failed", None, None)

            self.languages = language_payload.get("languages", [])
            self.selected_language = language_payload.get("selectedLanguage", self.selected_language)
            language_key = self.selected_language["key"]

            _, pending_payload = list_pending(language_key=language_key, server_base=self.server_base)
            _, history_payload = get_history(language_key=language_key, server_base=self.server_base)

            self.pending_items = pending_payload.get("pending", [])
            self.history_entries = history_payload.get("entries", [])
            self.selected_pending_id = choose_selected_pending_id(
                self.pending_items,
                self.selected_pending_id,
            )
            self._set_status("Ready for the next detection.", "success")
            if self.current_target_label:
                self.current_target_label.configure(text=self.selected_language["label"])
            if self.updated_label:
                now = datetime.now()
                hour = now.strftime("%I").lstrip("0") or "0"
                self.updated_label.configure(
                    text=f"Last synced at {now.strftime('%B')} {now.day}, {hour}:{now.strftime('%M %p')}"
                )
        except Exception as exc:
            self._set_status(f"Could not reach LanGo backend: {exc}", "error")
        finally:
            self._render_content()
            self._schedule_refresh()

    def _schedule_refresh(self):
        self._cancel_poll()
        self.poll_job = self.root.after(self.poll_ms, self._refresh_data)

    def _cancel_poll(self):
        if self.poll_job:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None

    def _render_content(self):
        if not self.content_frame:
            return
        for child in self.content_frame.winfo_children():
            child.destroy()
        if self.active_tab == "language":
            self._render_language_view()
            return
        self._render_mode_view()

    def _render_language_view(self):
        card = self._make_panel(self.content_frame)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Preferences", bg=THEME["surface"], fg=THEME["muted"], font=META_FONT).pack(anchor="w")
        tk.Label(card, text="Language", bg=THEME["surface"], fg=THEME["ink"], font=SECTION_FONT).pack(anchor="w", pady=(8, 18))

        grid = tk.Frame(card, bg=THEME["surface"])
        grid.pack(fill="both", expand=True)

        columns = 2
        for index, language in enumerate(self.languages):
            row = index // columns
            column = index % columns
            is_selected = language["key"] == self.selected_language["key"]
            button = tk.Button(
                grid,
                text=language["label"],
                command=lambda key=language["key"]: self._handle_language_change(key),
                bg=THEME["accent_soft"] if is_selected else THEME["paper_strong"],
                fg=THEME["ink"],
                activebackground=THEME["accent"],
                activeforeground=THEME["ink"],
                relief="flat",
                padx=24,
                pady=18,
                font=BODY_BOLD_FONT,
                cursor="hand2",
                wraplength=220,
            )
            button.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
            grid.grid_columnconfigure(column, weight=1)

        tk.Label(
            card,
            text="The detector uses this language for all new object submissions.",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=BODY_FONT,
        ).pack(anchor="w", pady=(18, 0))

    def _render_mode_view(self):
        shell = tk.Frame(self.content_frame, bg=THEME["paper"])
        shell.pack(fill="both", expand=True)

        mode_bar = self._make_panel(shell, padx=22, pady=18)
        mode_bar.pack(fill="x", pady=(0, 14))

        tk.Label(mode_bar, text="Device Mode", bg=THEME["surface"], fg=THEME["muted"], font=META_FONT).pack(anchor="w")
        mode_buttons = tk.Frame(mode_bar, bg=THEME["surface"])
        mode_buttons.pack(anchor="w", pady=(12, 0))
        for label, key in (("Learn", "learn"), ("Game", "game")):
            is_selected = self.current_mode == key
            tk.Button(
                mode_buttons,
                text=label,
                command=lambda value=key: self._switch_mode(value),
                bg=THEME["accent_soft"] if is_selected else THEME["paper_strong"],
                fg=THEME["ink"],
                activebackground=THEME["accent"],
                activeforeground=THEME["ink"],
                relief="flat",
                padx=18,
                pady=10,
                font=BODY_BOLD_FONT,
                cursor="hand2",
            ).pack(side="left", padx=(0, 10))

        if self.current_mode == "game":
            placeholder = self._make_panel(shell)
            placeholder.pack(fill="both", expand=True)
            tk.Label(placeholder, text="Game", bg=THEME["surface"], fg=THEME["ink"], font=SECTION_FONT).pack(anchor="w")
            tk.Label(
                placeholder,
                text="Game mode is still a placeholder on Raspberry Pi. Use Learn to manage detected words.",
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=BODY_FONT,
                wraplength=600,
                justify="left",
            ).pack(anchor="w", pady=(10, 0))
            return

        learn_shell = tk.Frame(shell, bg=THEME["paper"])
        learn_shell.pack(fill="both", expand=True)
        learn_shell.grid_columnconfigure(0, weight=1)
        learn_shell.grid_columnconfigure(1, weight=1)
        learn_shell.grid_rowconfigure(0, weight=1)

        queue_panel = self._make_panel(learn_shell)
        queue_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._render_queue_panel(queue_panel)

        detail_column = tk.Frame(learn_shell, bg=THEME["paper"])
        detail_column.grid(row=0, column=1, sticky="nsew")
        detail_column.grid_rowconfigure(0, weight=1)

        detail_panel = self._make_panel(detail_column)
        detail_panel.pack(fill="both", expand=True, pady=(0, 10))
        self._render_detail_panel(detail_panel)

        history_panel = self._make_panel(detail_column, padx=22, pady=20)
        history_panel.pack(fill="x")
        self._render_history_summary(history_panel)

    def _render_queue_panel(self, parent):
        tk.Label(parent, text="Raspberry Pi Queue", bg=THEME["surface"], fg=THEME["muted"], font=META_FONT).pack(anchor="w")
        tk.Label(parent, text="Pending Detection", bg=THEME["surface"], fg=THEME["ink"], font=SECTION_FONT).pack(anchor="w", pady=(8, 6))
        tk.Label(
            parent,
            text=f"{len(self.pending_items)} item{'s' if len(self.pending_items) != 1 else ''} waiting for confirmation",
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=BODY_FONT,
        ).pack(anchor="w")

        list_host = tk.Frame(parent, bg=THEME["surface"])
        list_host.pack(fill="both", expand=True, pady=(18, 0))

        canvas = tk.Canvas(
            list_host,
            bg=THEME["surface"],
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(
            list_host,
            orient="vertical",
            style="LanGo.Vertical.TScrollbar",
            command=canvas.yview,
        )
        rows = tk.Frame(canvas, bg=THEME["surface"])
        rows.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=rows, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if not self.pending_items:
            tk.Label(
                rows,
                text=f"No pending detections for {self.selected_language['label']}.",
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=BODY_FONT,
                pady=24,
            ).pack(fill="x")
            return

        for pending in self.pending_items:
            self._render_pending_row(rows, pending)

    def _render_pending_row(self, parent, pending):
        is_selected = pending.get("pendingId") == self.selected_pending_id
        row_bg = THEME["accent_soft"] if is_selected else THEME["paper_strong"]

        row = tk.Frame(
            parent,
            bg=row_bg,
            highlightbackground=THEME["line"],
            highlightthickness=1,
            padx=12,
            pady=12,
            cursor="hand2",
        )
        row.pack(fill="x", pady=(0, 10))
        row.bind("<Button-1>", lambda _event, pending_id=pending["pendingId"]: self._select_pending(pending_id))

        self._render_thumbnail(row, pending.get("image"), pending.get("english", ""), 72).pack(side="left")

        copy = tk.Frame(row, bg=row_bg)
        copy.pack(side="left", fill="both", expand=True, padx=(12, 0))
        for widget in (
            tk.Label(copy, text=pending.get("english", ""), bg=row_bg, fg=THEME["ink"], font=("Avenir Next", 18, "bold"), anchor="w"),
            tk.Label(copy, text=pending.get("translated", ""), bg=row_bg, fg="#855d1d", font=("Avenir Next", 16), anchor="w"),
            tk.Label(copy, text=format_display_time(pending.get("createdAt"), ""), bg=row_bg, fg=THEME["muted"], font=("Avenir Next", 11), anchor="w"),
        ):
            widget.pack(anchor="w")
            widget.bind("<Button-1>", lambda _event, pending_id=pending["pendingId"]: self._select_pending(pending_id))

    def _render_detail_panel(self, parent):
        tk.Label(parent, text="Learn", bg=THEME["surface"], fg=THEME["muted"], font=META_FONT).pack(anchor="w")
        tk.Label(parent, text="Selected Detection", bg=THEME["surface"], fg=THEME["ink"], font=SECTION_FONT).pack(anchor="w", pady=(8, 18))

        selected = self._selected_pending_item()
        if not selected:
            tk.Label(
                parent,
                text="Waiting for a detected word. Point at an object and then pick it from the queue.",
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=BODY_FONT,
                wraplength=440,
                justify="left",
            ).pack(anchor="w")
            return

        detail_top = tk.Frame(parent, bg=THEME["surface"])
        detail_top.pack(fill="x")
        self._render_thumbnail(detail_top, selected.get("image"), selected.get("english", ""), 180).pack(anchor="w")

        tk.Label(
            parent,
            text=selected.get("english", ""),
            bg=THEME["surface"],
            fg=THEME["ink"],
            font=("Avenir Next", 24, "bold"),
        ).pack(anchor="w", pady=(18, 4))
        tk.Label(
            parent,
            text=selected.get("translated", ""),
            bg=THEME["surface"],
            fg="#855d1d",
            font=("Avenir Next", 20),
        ).pack(anchor="w")
        tk.Label(
            parent,
            text=format_display_time(selected.get("createdAt"), ""),
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=BODY_FONT,
        ).pack(anchor="w", pady=(10, 18))

        actions = tk.Frame(parent, bg=THEME["surface"])
        actions.pack(anchor="w")

        tk.Button(
            actions,
            text="Add to History",
            command=self._confirm_selected_pending,
            bg=THEME["accent_soft"],
            fg=THEME["ink"],
            activebackground=THEME["accent"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=18,
            pady=12,
            font=BUTTON_FONT,
            cursor="hand2",
        ).pack(side="left", padx=(0, 12))
        tk.Button(
            actions,
            text="Reject",
            command=self._reject_selected_pending,
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            activebackground=THEME["warm"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=18,
            pady=12,
            font=BUTTON_FONT,
            cursor="hand2",
        ).pack(side="left")

    def _render_history_summary(self, parent):
        tk.Label(parent, text="Session Log", bg=THEME["surface"], fg=THEME["muted"], font=META_FONT).pack(anchor="w")
        tk.Label(parent, text="Latest Translation", bg=THEME["surface"], fg=THEME["ink"], font=("Avenir Next Condensed", 22, "bold")).pack(anchor="w", pady=(8, 12))

        if not self.history_entries:
            tk.Label(
                parent,
                text=f"No history yet for {self.selected_language['label']}.",
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=BODY_FONT,
            ).pack(anchor="w")
            return

        latest = self.history_entries[0]
        tk.Label(parent, text=latest.get("english", ""), bg=THEME["surface"], fg=THEME["ink"], font=BODY_BOLD_FONT).pack(anchor="w")
        tk.Label(parent, text=latest.get("translated", ""), bg=THEME["surface"], fg="#855d1d", font=BODY_FONT).pack(anchor="w")
        tk.Label(
            parent,
            text=format_display_time(latest.get("createdAt"), latest.get("time", "")),
            bg=THEME["surface"],
            fg=THEME["muted"],
            font=("Avenir Next", 12),
        ).pack(anchor="w", pady=(6, 0))

    def _selected_pending_item(self):
        for pending in self.pending_items:
            if pending.get("pendingId") == self.selected_pending_id:
                return pending
        return None

    def _select_pending(self, pending_id):
        self.selected_pending_id = pending_id
        self._render_content()

    def _handle_language_change(self, language_key):
        try:
            _, payload = set_selected_language(language_key, server_base=self.server_base)
            self.selected_language = payload.get("selectedLanguage", self.selected_language)
            self.languages = payload.get("languages", self.languages)
            self._set_status(f"{self.selected_language['label']} is now active for new detections.", "success")
            self._refresh_data()
        except Exception as exc:
            self._set_status(f"Could not switch language: {exc}", "error")

    def _confirm_selected_pending(self):
        selected = self._selected_pending_item()
        if not selected:
            return
        try:
            _, payload = confirm_pending(selected["pendingId"], server_base=self.server_base)
            entry = payload.get("entry", {})
            self._set_status(
                f"Saved {entry.get('english', selected.get('english', 'item'))} to translation history.",
                "success",
            )
            self._refresh_data()
        except Exception as exc:
            self._set_status(f"Could not add item to history: {exc}", "error")

    def _reject_selected_pending(self):
        selected = self._selected_pending_item()
        if not selected:
            return
        try:
            reject_pending(selected["pendingId"], server_base=self.server_base)
            self._set_status(f"Rejected {selected.get('english', 'item')}.", "success")
            self._refresh_data()
        except Exception as exc:
            self._set_status(f"Could not reject item: {exc}", "error")

    def _make_panel(self, parent, padx=28, pady=24):
        return tk.Frame(
            parent,
            bg=THEME["surface"],
            highlightbackground=THEME["line"],
            highlightthickness=1,
            padx=padx,
            pady=pady,
        )

    def _render_thumbnail(self, parent, image_path, fallback_label, target_size):
        container = tk.Frame(
            parent,
            bg=THEME["surface_alt"],
            width=target_size,
            height=target_size,
            highlightbackground=THEME["line"],
            highlightthickness=1,
        )
        container.pack_propagate(False)

        image = self._load_supported_photo(image_path, target_size)
        if image:
            label = tk.Label(container, image=image, bg=THEME["surface_alt"])
            label.image = image
            label.pack(fill="both", expand=True)
            return container

        tk.Label(
            container,
            text=(fallback_label[:10] or "No image"),
            bg=THEME["surface_alt"],
            fg=THEME["muted"],
            font=("Avenir Next", 10, "bold"),
            wraplength=target_size - 10,
            justify="center",
        ).pack(fill="both", expand=True)
        return container

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
