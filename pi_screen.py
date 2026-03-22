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

TITLE_FONT = ("Avenir Next Condensed", 34, "bold")
BODY_FONT = ("Avenir Next", 16)
BODY_BOLD_FONT = ("Avenir Next", 16, "bold")
META_FONT = ("Avenir Next", 10, "bold")
DISPLAY_FONT = ("Avenir Next", 24)
DISPLAY_BOLD_FONT = ("Avenir Next", 28, "bold")
TOUCH_FONT = ("Avenir Next", 20, "bold")
TOUCH_FONT_SMALL = ("Avenir Next", 18, "bold")


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


def format_main_message(mode_key, selected_pending, latest_entry):
    if mode_key == "game":
        return "game mode coming soon"
    if selected_pending:
        return f"{selected_pending.get('english', '')} \u2192 {selected_pending.get('translated', '')}"
    if latest_entry:
        return f"{latest_entry.get('english', '')} \u2192 {latest_entry.get('translated', '')}"
    return "point to start translating"


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
        self.settings_tab = "language"
        self.current_mode = "learn"
        self.show_settings = False
        self.status_message = "Connecting to LanGo..."
        self.status_tone = "muted"
        self.image_cache = {}
        self.poll_job = None

        self.shell = None
        self.status_label = None
        self.content_frame = None

        self._configure_root()
        self._configure_style()
        self._build_shell()
        self._refresh_data()

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

    def _cancel_poll(self):
        if self.poll_job:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None

    def _schedule_refresh(self):
        self._cancel_poll()
        self.poll_job = self.root.after(self.poll_ms, self._refresh_data)

    def _build_shell(self):
        for child in self.root.winfo_children():
            child.destroy()

        self.shell = tk.Frame(self.root, bg=THEME["paper"])
        self.shell.pack(fill="both", expand=True, padx=24, pady=24)

        self.status_label = tk.Label(
            self.shell,
            text=self.status_message,
            bg=THEME["paper"],
            fg=THEME["muted"],
            font=("Avenir Next", 12),
        )
        self.status_label.pack(fill="x", anchor="w", pady=(0, 8))

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

        self._add_gear_button(stage).place(relx=0.97, rely=0.06, anchor="ne")

        main_message = format_main_message(
            self.current_mode,
            self._selected_pending_item(),
            self.history_entries[0] if self.history_entries else None,
        )

        center = tk.Frame(stage, bg=THEME["paper_strong"])
        center.place(relx=0.5, rely=0.38, anchor="center")

        tk.Label(
            center,
            text=main_message,
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            font=DISPLAY_FONT if "\u2192" in main_message else DISPLAY_BOLD_FONT,
        ).pack()

        footer = tk.Frame(stage, bg=THEME["paper_strong"])
        footer.place(relx=0.5, rely=0.84, anchor="s", relwidth=0.86, relheight=0.34)

        if self.current_mode == "game":
            self._render_game_placeholder(footer)
            return

        self._render_pending_footer(footer)

    def _render_game_placeholder(self, parent):
        tk.Label(
            parent,
            text="Game",
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            parent,
            text="Game mode is visible here, but still not functional on Raspberry Pi.",
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            font=BODY_FONT,
            wraplength=680,
            justify="left",
        ).pack(anchor="w")

    def _render_pending_footer(self, parent):
        selected = self._selected_pending_item()

        header = tk.Frame(parent, bg=THEME["paper_strong"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="Learn Queue",
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(side="left")
        tk.Label(
            header,
            text=f"{len(self.pending_items)} pending",
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=("Avenir Next", 11),
        ).pack(side="right")

        if not self.pending_items:
            tk.Label(
                parent,
                text=f"No pending detections for {self.selected_language['label']}.",
                bg=THEME["paper_strong"],
                fg=THEME["muted"],
                font=BODY_FONT,
            ).pack(anchor="center", pady=(28, 0))
            return

        list_host = tk.Frame(parent, bg=THEME["paper_strong"])
        list_host.pack(fill="both", expand=True, pady=(14, 12))

        canvas = tk.Canvas(list_host, bg=THEME["paper_strong"], bd=0, highlightthickness=0, height=110)
        scrollbar = ttk.Scrollbar(
            list_host,
            orient="horizontal",
            style="LanGo.Horizontal.TScrollbar",
            command=canvas.xview,
        )
        rows = tk.Frame(canvas, bg=THEME["paper_strong"])
        rows.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=rows, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        canvas.pack(fill="both", expand=True)
        scrollbar.pack(fill="x", pady=(8, 0))

        for pending in self.pending_items:
            self._render_pending_chip(rows, pending)

        action_bar = tk.Frame(parent, bg=THEME["paper_strong"])
        action_bar.pack(fill="x")

        if selected:
            meta_text = f"{selected.get('english', '')} \u2192 {selected.get('translated', '')}  \u2022  {format_display_time(selected.get('createdAt'), '')}"
        else:
            meta_text = "Select a detected word to confirm or reject it."

        tk.Label(
            action_bar,
            text=meta_text,
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=("Avenir Next", 12),
        ).pack(side="left")

        controls = tk.Frame(action_bar, bg=THEME["paper_strong"])
        controls.pack(side="right")
        tk.Button(
            controls,
            text="Add to History",
            command=self._confirm_selected_pending,
            bg=THEME["accent"] if selected else THEME["accent_soft"],
            fg=THEME["ink"],
            activebackground=THEME["accent_strong"],
            activeforeground=THEME["ink"],
            relief="flat",
            state="normal" if selected else "disabled",
            padx=16,
            pady=10,
            font=BODY_BOLD_FONT,
            cursor="hand2" if selected else "arrow",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            controls,
            text="Reject",
            command=self._reject_selected_pending,
            bg=THEME["surface_alt"],
            fg=THEME["ink"],
            activebackground=THEME["warm"],
            activeforeground=THEME["ink"],
            relief="flat",
            state="normal" if selected else "disabled",
            padx=16,
            pady=10,
            font=BODY_BOLD_FONT,
            cursor="hand2" if selected else "arrow",
        ).pack(side="left")

    def _render_pending_chip(self, parent, pending):
        is_selected = pending.get("pendingId") == self.selected_pending_id
        bg = THEME["accent"] if is_selected else THEME["surface_alt"]

        chip = tk.Frame(
            parent,
            bg=bg,
            padx=14,
            pady=12,
            cursor="hand2",
            highlightbackground=THEME["line"],
            highlightthickness=0 if is_selected else 1,
        )
        chip.pack(side="left", padx=(0, 12))
        chip.bind("<Button-1>", lambda _event, pending_id=pending["pendingId"]: self._select_pending(pending_id))

        tk.Label(
            chip,
            text=pending.get("english", ""),
            bg=bg,
            fg=THEME["ink"],
            font=BODY_BOLD_FONT,
        ).pack(anchor="w")
        tk.Label(
            chip,
            text=pending.get("translated", ""),
            bg=bg,
            fg=THEME["ink"],
            font=("Avenir Next", 13),
        ).pack(anchor="w")

    def _render_settings_screen(self):
        stage = self._make_stage(self.content_frame)
        stage.pack(fill="both", expand=True)

        self._add_gear_button(stage).place(relx=0.97, rely=0.06, anchor="ne")

        slider = tk.Frame(stage, bg=THEME["surface_alt"], padx=8, pady=8)
        slider.place(relx=0.5, rely=0.10, anchor="n")

        self._make_slider_button(slider, "Language", "language").pack(side="left", padx=(0, 8))
        self._make_slider_button(slider, "Mode", "mode").pack(side="left")

        settings_card = tk.Frame(
            stage,
            bg=THEME["paper_strong"],
            highlightbackground=THEME["line"],
            highlightthickness=1,
            padx=18,
            pady=18,
        )
        settings_card.place(relx=0.5, rely=0.24, anchor="n", relwidth=0.86, relheight=0.68)

        title_text = "Select language" if self.settings_tab == "language" else "Select mode"
        tk.Label(
            settings_card,
            text=title_text,
            bg=THEME["paper_strong"],
            fg=THEME["muted"],
            font=META_FONT,
        ).pack(anchor="w", pady=(0, 10))

        body_host = tk.Frame(settings_card, bg=THEME["paper_strong"])
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

        canvas = tk.Canvas(parent, bg=THEME["paper_strong"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            style="LanGo.Vertical.TScrollbar",
            command=canvas.yview,
        )
        grid = tk.Frame(canvas, bg=THEME["paper_strong"])
        grid.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        columns = 2
        for index, language in enumerate(self.languages):
            row = index // columns
            column = index % columns
            is_selected = language["key"] == self.selected_language["key"]
            button = self._make_option_button(
                grid,
                language["label"],
                is_selected,
                lambda key=language["key"]: self._handle_language_change(key),
            )
            button.grid(row=row, column=column, padx=12, pady=12, sticky="nsew")
            grid.grid_columnconfigure(column, weight=1, uniform="language-column")

    def _render_mode_buttons(self, parent):
        wrap = tk.Frame(parent, bg=THEME["paper_strong"])
        wrap.pack(expand=True)

        for index, (label, key) in enumerate((("Learn", "learn"), ("Game", "game"))):
            is_selected = self.current_mode == key
            button = self._make_option_button(
                wrap,
                label,
                is_selected,
                lambda value=key: self._switch_mode(value),
            )
            button.grid(row=index, column=0, padx=18, pady=18, sticky="ew")
        wrap.grid_columnconfigure(0, weight=1)

    def _make_option_button(self, parent, text, is_selected, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=THEME["accent"] if is_selected else THEME["surface_alt"],
            fg=THEME["ink"],
            activebackground=THEME["accent_strong"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=36,
            pady=20,
            font=TOUCH_FONT,
            cursor="hand2",
            width=12,
        )

    def _make_slider_button(self, parent, text, tab_key):
        is_selected = self.settings_tab == tab_key
        return tk.Button(
            parent,
            text=text,
            command=lambda: self._switch_settings_tab(tab_key),
            bg=THEME["accent"] if is_selected else THEME["surface_alt"],
            fg=THEME["ink"],
            activebackground=THEME["accent_strong"],
            activeforeground=THEME["ink"],
            relief="flat",
            padx=34,
            pady=14,
            font=TOUCH_FONT_SMALL,
            cursor="hand2",
            width=9,
        )

    def _make_stage(self, parent):
        stage = tk.Frame(
            parent,
            bg=THEME["paper_strong"],
            highlightbackground="#ff3b30",
            highlightthickness=1,
        )
        return stage

    def _add_gear_button(self, parent):
        return tk.Button(
            parent,
            text="\u2699",
            command=self._toggle_settings,
            bg=THEME["paper_strong"],
            fg=THEME["ink"],
            activebackground=THEME["paper_strong"],
            activeforeground=THEME["ink"],
            relief="flat",
            bd=0,
            padx=6,
            pady=4,
            font=("Avenir Next", 28),
            cursor="hand2",
        )

    def _toggle_settings(self):
        self.show_settings = not self.show_settings
        self._render_screen()

    def _switch_settings_tab(self, tab_key):
        self.settings_tab = tab_key
        self._render_screen()

    def _switch_mode(self, mode_key):
        self.current_mode = mode_key
        self._set_status(f"{mode_key.title()} mode selected.", "success")
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
            self.selected_pending_id = choose_selected_pending_id(self.pending_items, self.selected_pending_id)
            self._set_status(
                f"{self.selected_language['label']} ready. {len(self.pending_items)} item{'s' if len(self.pending_items) != 1 else ''} waiting.",
                "success",
            )
        except Exception as exc:
            self._set_status(f"Could not reach LanGo backend: {exc}", "error")
        finally:
            self._render_screen()
            self._schedule_refresh()

    def _selected_pending_item(self):
        for pending in self.pending_items:
            if pending.get("pendingId") == self.selected_pending_id:
                return pending
        return None

    def _select_pending(self, pending_id):
        self.selected_pending_id = pending_id
        self._render_screen()

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
            self._set_status(f"Saved {entry.get('english', selected.get('english', 'item'))} to history.", "success")
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
