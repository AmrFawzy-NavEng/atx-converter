# ATX-Converter/pcc_convertor.py
"""
ATX-Converter -- Standalone GUI for ANTEX format conversion.
Converts between ANTEX v1.4 and v2.0, with antenna/signal filtering.

Part of the PCC software suite by IfE, Leibniz Universitaet Hannover.
"""

import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Resolve import paths
_this_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_this_dir)
_explorer_dir = os.path.join(_parent_dir, 'ImpactOfDeltaPCC')
if os.path.isdir(_explorer_dir):
    sys.path.insert(0, _explorer_dir)
sys.path.insert(0, _this_dir)

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import numpy as np
from PIL import Image, ImageTk, ImageEnhance
from src.data_io import read_antex_file
from antex_writer import write_antex_v14, write_antex_v2

# Shared opt-in dialog for the IfE software mailing list. Never let a missing
# copy stop the program from starting; the canonical file is in shared/.
try:
    import mailing_list
except Exception:
    mailing_list = None

# Version and release date, from this tool's own tool_version.py. The same pair
# sits in the README tag that the PCC-Suite launcher reads, so the launcher no
# longer has to guess a release from a file timestamp.
try:
    import tool_version
    import version_info
    VERSION_TEXT = version_info.about_line(tool_version)
except Exception:
    VERSION_TEXT = "Version: unknown"


# --- PATH HELPER FOR EXE ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class CreateToolTip:
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text='widget info'):
        self.waittime = 500
        self.wraplength = 300
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def leave(self, event=None):
        self.unschedule()
        if self.tw:
            self.tw.destroy()
            self.tw = None

    def unschedule(self):
        _id = self.id
        self.id = None
        if _id:
            self.widget.after_cancel(_id)

    def showtip(self, event=None):
        try:
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 20
        except (tk.TclError, TypeError):
            # bbox("insert") fails on Button/Label widgets (no text cursor)
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength=self.wraplength)
        label.pack(ipadx=1)


def _show_ife_contact(parent):
    """
    IfE contact dialog with clickable e-mail and web links.

    Same content and layout as PCC-Explorer's, so every tool in the suite
    presents its contact details identically.
    """
    import webbrowser

    dialog = tk.Toplevel(parent)
    dialog.title("Contact Information")
    dialog.geometry("460x300")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Institut für Erdmessung (IfE)",
              font=("Helvetica", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Leibniz Universität Hannover").pack(anchor="w")
    ttk.Label(frame, text="Schneiderberg 50").pack(anchor="w")
    ttk.Label(frame, text="D-30167 Hannover").pack(anchor="w", pady=(0, 15))

    ttk.Label(frame, text="Contact: Dr.-Ing. Johannes Kröger",
              font=("Helvetica", 10, "bold")).pack(anchor="w")

    email_frame = ttk.Frame(frame)
    email_frame.pack(anchor="w", pady=2)
    ttk.Label(email_frame, text="Email: ").pack(side="left")
    email_link = ttk.Label(email_frame, text="kroeger@ife.uni-hannover.de",
                           foreground="#4da6ff", cursor="hand2")
    email_link.pack(side="left")
    email_link.bind("<Button-1>",
                    lambda e: webbrowser.open("mailto:kroeger@ife.uni-hannover.de"))

    web_frame = ttk.Frame(frame)
    web_frame.pack(anchor="w", pady=2)
    ttk.Label(web_frame, text="Web: ").pack(side="left")
    web_link = ttk.Label(web_frame, text="www.ife.uni-hannover.de",
                         foreground="#4da6ff", cursor="hand2")
    web_link.pack(side="left")
    web_link.bind("<Button-1>",
                  lambda e: webbrowser.open("https://www.ife.uni-hannover.de"))

    def _open_mailing_list():
        # Close first. Two stacked modal dialogs each take the grab, and the
        # inner one releasing it would leave this window unresponsive.
        dialog.destroy()
        try:
            parent._show_mailing_list()
        except Exception:
            pass

    buttons = ttk.Frame(frame)
    buttons.pack(pady=(20, 0))
    ttk.Button(buttons, text="Mailing list", command=_open_mailing_list,
               bootstyle="outline-info").pack(side="left", padx=4)
    ttk.Button(buttons, text="Close", command=dialog.destroy,
               bootstyle="secondary").pack(side="left", padx=4)

    # Size to the content, with 460x300 as the minimum: a fixed size would cut
    # the buttons off on systems with larger fonts or display scaling.
    dialog.update_idletasks()
    dialog.geometry("%dx%d" % (max(460, dialog.winfo_reqwidth()),
                               max(300, dialog.winfo_reqheight())))


class PCCConvertorApp(ttk.Window):
    """Main application window for ATX-Converter."""

    def __init__(self):
        super().__init__(title="ATX-Converter", themename="darkly")

        self.geometry("780x750")
        self.minsize(700, 650)

        # State
        self.antex_data = None
        self.source_path = None
        self.detected_version = None

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._build_ui()
        self._fit_top_bar()

    def _fit_top_bar(self):
        """
        Widen the window if the header row does not fit in it.

        The window size is set in pixels while the fonts follow the system
        text scaling, so with larger system text the header row can run off the
        edge and truncate its buttons. Measuring what the row needs is the only
        thing that holds on any display.
        """
        try:
            bar = getattr(self, "_top_bar", None)
            if bar is None:
                return
            self.update_idletasks()
            need = bar.winfo_reqwidth() + 8
            if need <= self.winfo_width():
                return
            height = self.winfo_height()
            self.geometry("%dx%d" % (need, height))
            min_w, min_h = self.minsize()
            if need > min_w:
                self.minsize(need, min_h)
        except Exception as exc:
            print("[WARNING] Could not fit the header row: %s" % exc)

    def _on_closing(self):
        self.destroy()

    def _build_ui(self):
        """Build the complete GUI layout."""
        # === TOP BAR (matching PCC-Explorer / RINEX-Masker) ===
        top_bar = ttk.Frame(self, padding=10)
        top_bar.pack(fill='x')
        # Kept so the window can be widened if this row does not fit.
        self._top_bar = top_bar

        # Left: IfE logo + title
        left_frame = ttk.Frame(top_bar)
        left_frame.pack(side='left')

        self.logo_img = None
        ife_logo_path = resource_path(os.path.join('assets', 'ife_logo.png'))
        if os.path.exists(ife_logo_path):
            try:
                pil_image = Image.open(ife_logo_path)
                aspect = pil_image.width / pil_image.height
                h = 45
                resized = pil_image.resize((int(h * aspect), h), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(resized)
                ttk.Label(left_frame, image=self.logo_img).pack(side='left', padx=(0, 12))
            except Exception:
                pass

        text_frame = ttk.Frame(left_frame)
        text_frame.pack(side='left')
        ttk.Label(text_frame, text="ATX-Converter", font=('Helvetica', 18, 'bold')).pack(anchor='w')
        ttk.Label(text_frame, text="Institut f\u00fcr Erdmessung (IfE)", font=('Helvetica', 10), bootstyle='light').pack(anchor='w')

        # Right: LUH logo
        self.luh_logo_img = None
        luh_logo_path = resource_path(os.path.join('assets', 'luh_logo.png'))
        if os.path.exists(luh_logo_path):
            try:
                pil_luh = Image.open(luh_logo_path)
                h = 50
                aspect = pil_luh.width / pil_luh.height
                resized_luh = pil_luh.resize((int(h * aspect), h), Image.Resampling.LANCZOS)
                enhancer = ImageEnhance.Sharpness(resized_luh)
                final_luh = enhancer.enhance(1.5)
                self.luh_logo_img = ImageTk.PhotoImage(final_luh)
                luh_frame = ttk.Frame(top_bar)
                luh_frame.pack(side='right', padx=(10, 0))
                ttk.Label(luh_frame, image=self.luh_logo_img).pack(side='right')
            except Exception:
                pass

        # Middle-Right: Info buttons
        btn_frame = ttk.Frame(top_bar)
        btn_frame.pack(side='right', padx=15)
        ttk.Button(btn_frame, text='Contact', command=self._show_contact, bootstyle='outline-info').pack(side='left', padx=3)
        ttk.Button(btn_frame, text='Information', command=self._show_about, bootstyle='outline-secondary').pack(side='left', padx=3)

        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=(0, 5))

        # --- Input Section ---
        input_frame = ttk.LabelFrame(self, text="  Input ANTEX File  ", padding=10)
        input_frame.pack(fill='x', padx=10, pady=5)

        row1 = ttk.Frame(input_frame)
        row1.pack(fill='x', pady=2)
        ttk.Label(row1, text="File:").pack(side='left')
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(row1, textvariable=self.file_var, width=55)
        self.file_entry.pack(side='left', padx=5, expand=True, fill='x')
        ttk.Button(row1, text="Browse...", command=self._browse_file).pack(side='left')

        row2 = ttk.Frame(input_frame)
        row2.pack(fill='x', pady=5)
        ttk.Label(row2, text="Detected Format:").pack(side='left')
        self.format_label = ttk.Label(row2, text="—", font=('Helvetica', 10, 'bold'))
        self.format_label.pack(side='left', padx=10)
        ttk.Label(row2, text="Antennas:").pack(side='left', padx=(20, 0))
        self.antenna_count_label = ttk.Label(row2, text="—")
        self.antenna_count_label.pack(side='left', padx=5)
        ttk.Label(row2, text="Signals:").pack(side='left', padx=(20, 0))
        self.signal_count_label = ttk.Label(row2, text="—")
        self.signal_count_label.pack(side='left', padx=5)

        # --- Antenna Filter ---
        filter_frame = ttk.LabelFrame(self, text="  Antenna & Signal Filter  ", padding=10)
        filter_frame.pack(fill='x', padx=10, pady=5)

        ant_row = ttk.Frame(filter_frame)
        ant_row.pack(fill='x', pady=2)
        ttk.Label(ant_row, text="Antenna:").pack(side='left')
        self.antenna_var = tk.StringVar(value="All")
        self.antenna_combo = ttk.Combobox(ant_row, textvariable=self.antenna_var,
                                          state='readonly', width=40)
        self.antenna_combo['values'] = ["All"]
        self.antenna_combo.pack(side='left', padx=5)
        self.antenna_combo.bind('<<ComboboxSelected>>', self._on_antenna_changed)

        sig_row = ttk.Frame(filter_frame)
        sig_row.pack(fill='x', pady=5)
        ttk.Label(sig_row, text="Signals:").pack(side='left', anchor='n')

        # Checkbox grid frame (replaces old Listbox)
        self.signal_check_frame = ttk.Frame(sig_row)
        self.signal_check_frame.pack(side='left', padx=5, fill='x', expand=True)
        self.signal_checkbuttons = {}  # {freq_code: tk.BooleanVar}

        sig_btn_row = ttk.Frame(filter_frame)
        sig_btn_row.pack(fill='x', pady=2)
        ttk.Button(sig_btn_row, text="Select All", command=self._select_all_signals).pack(side='left', padx=5)
        ttk.Button(sig_btn_row, text="Select None", command=self._select_no_signals).pack(side='left')
        ttk.Button(sig_btn_row, text="GPS", command=lambda: self._select_system('G')).pack(side='left', padx=5)
        ttk.Button(sig_btn_row, text="Galileo", command=lambda: self._select_system('E')).pack(side='left')
        ttk.Button(sig_btn_row, text="GLONASS", command=lambda: self._select_system('R')).pack(side='left', padx=5)
        ttk.Button(sig_btn_row, text="BeiDou", command=lambda: self._select_system('C')).pack(side='left')

        # --- Output Section ---
        output_frame = ttk.LabelFrame(self, text="  Output  ", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)

        fmt_row = ttk.Frame(output_frame)
        fmt_row.pack(fill='x', pady=2)
        ttk.Label(fmt_row, text="Output Format:").pack(side='left')
        self.output_format_var = tk.StringVar(value="ANTEX v1.4")
        ttk.Radiobutton(fmt_row, text="ANTEX v1.4", variable=self.output_format_var,
                        value="ANTEX v1.4").pack(side='left', padx=10)
        ttk.Radiobutton(fmt_row, text="ANTEX v2.0", variable=self.output_format_var,
                        value="ANTEX v2.0").pack(side='left', padx=10)

        out_row = ttk.Frame(output_frame)
        out_row.pack(fill='x', pady=5)
        ttk.Label(out_row, text="Save to:").pack(side='left')
        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(out_row, textvariable=self.output_var, width=55)
        self.output_entry.pack(side='left', padx=5, expand=True, fill='x')
        ttk.Button(out_row, text="Browse...", command=self._browse_output).pack(side='left')

        # --- Preview ---
        preview_frame = ttk.LabelFrame(self, text="  Preview  ", padding=5)
        preview_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.preview_text = tk.Text(preview_frame, height=8, wrap='none',
                                    font=('Consolas', 9), state='disabled')
        self.preview_text.pack(fill='both', expand=True)
        prev_scroll = ttk.Scrollbar(self.preview_text, orient='vertical',
                                     command=self.preview_text.yview)
        prev_scroll.pack(side='right', fill='y')
        self.preview_text.config(yscrollcommand=prev_scroll.set)

        # --- Action Buttons ---
        btn_bar = ttk.Frame(self, padding=10)
        btn_bar.pack(fill='x')

        ttk.Button(btn_bar, text="Convert & Export", bootstyle="success",
                   command=self._do_convert).pack(side='left', padx=5)
        preview_btn = ttk.Button(btn_bar, text="Preview Converted Output", bootstyle="info-outline",
                                 command=self._do_preview)
        preview_btn.pack(side='left', padx=5)
        CreateToolTip(preview_btn,
                      "Shows what the OUTPUT file will look like after conversion\n"
                      "(not the original input file).")
        ttk.Button(btn_bar, text="Quit", command=self._on_closing, bootstyle="danger-outline").pack(side='right', padx=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready. Load an ANTEX file to begin.")
        ttk.Label(self, textvariable=self.status_var, relief='sunken',
                  anchor='w', padding=3).pack(fill='x', side='bottom')

    # --- Callbacks ---

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select ANTEX File",
            filetypes=[("ANTEX files", "*.atx *.atx2"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)
            self._load_file(path)

    def _browse_output(self):
        fmt = self.output_format_var.get()
        ext = ".atx" if "1.4" in fmt else ".atx2"
        path = filedialog.asksaveasfilename(
            title="Save Converted ANTEX File",
            defaultextension=ext,
            filetypes=[("ANTEX files", f"*{ext}"), ("All files", "*.*")]
        )
        if path:
            self.output_var.set(path)

    def _load_file(self, path: str):
        """Load and parse the ANTEX file."""
        self.status_var.set(f"Loading {os.path.basename(path)}...")
        self.update_idletasks()

        try:
            self.antex_data = read_antex_file(path)
            self.source_path = path
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to parse ANTEX file:\n{e}")
            self.status_var.set("Error loading file.")
            return

        # Detect version
        try:
            with open(path, 'r') as f:
                first_line = f.readline()
            if '2' in first_line[:10].split('.')[0] if '.' in first_line[:10] else first_line[:10].strip().startswith('2'):
                self.detected_version = "v2.0"
            else:
                self.detected_version = "v1.4"
        except:
            self.detected_version = "v1.4"

        self.format_label.config(text=f"ANTEX {self.detected_version}")

        # Populate antenna dropdown
        antennas = sorted(self.antex_data.get('metadata', {}).keys())
        self.antenna_combo['values'] = ["All"] + antennas
        self.antenna_var.set("All")
        self.antenna_count_label.config(text=str(len(antennas)))

        # Populate signal list
        self._populate_signals()

        # Auto-suggest output path
        base, ext = os.path.splitext(path)
        if self.detected_version == "v1.4":
            self.output_format_var.set("ANTEX v1.4")
            self.output_var.set(base + "_converted.atx")
        else:
            self.output_format_var.set("ANTEX v1.4")
            self.output_var.set(base + "_converted.atx")

        self.status_var.set(f"Loaded: {len(antennas)} antenna(s), {len(self.signal_checkbuttons)} signal(s)")

    def _populate_signals(self, antenna_key=None):
        """Populate signal checkbox grid based on selected antenna."""
        # Clear existing checkboxes
        for widget in self.signal_check_frame.winfo_children():
            widget.destroy()
        self.signal_checkbuttons.clear()

        if not self.antex_data:
            return

        pco_data = self.antex_data.get('pco', {})
        signals = set()

        if antenna_key and antenna_key != "All":
            for sys_name, freqs in pco_data.get(antenna_key, {}).items():
                signals.update(freqs.keys())
        else:
            for ant_key, systems in pco_data.items():
                for sys_name, freqs in systems.items():
                    signals.update(freqs.keys())

        # Group signals by system prefix
        SYS_NAMES = {'G': 'GPS', 'E': 'Galileo', 'R': 'GLONASS', 'C': 'BeiDou',
                     'J': 'QZSS', 'S': 'SBAS', 'I': 'IRNSS'}
        grouped = {}
        for sig in sorted(signals):
            prefix = sig[0] if sig else '?'
            sys_name = SYS_NAMES.get(prefix, prefix)
            grouped.setdefault(sys_name, []).append(sig)

        col = 0
        for sys_name in ['GPS', 'Galileo', 'GLONASS', 'BeiDou', 'QZSS', 'SBAS', 'IRNSS']:
            if sys_name not in grouped:
                continue
            sys_frame = ttk.LabelFrame(self.signal_check_frame, text=sys_name, padding=3)
            sys_frame.grid(row=0, column=col, padx=4, pady=2, sticky='nsew')
            for row_idx, sig in enumerate(grouped[sys_name]):
                var = tk.BooleanVar(value=True)
                ttk.Checkbutton(sys_frame, text=sig, variable=var).grid(
                    row=row_idx, column=0, sticky='w', padx=2)
                self.signal_checkbuttons[sig] = var
            col += 1

        self.signal_count_label.config(text=str(len(signals)))

    def _on_antenna_changed(self, event=None):
        ant = self.antenna_var.get()
        if ant == "All":
            self._populate_signals()
        else:
            self._populate_signals(ant)

    def _select_all_signals(self):
        for var in self.signal_checkbuttons.values():
            var.set(True)

    def _select_no_signals(self):
        for var in self.signal_checkbuttons.values():
            var.set(False)

    def _select_system(self, prefix: str):
        for sig, var in self.signal_checkbuttons.items():
            var.set(sig.startswith(prefix))

    def _get_filtered_data(self) -> dict:
        """Build a filtered copy of antex_data based on current selections."""
        if not self.antex_data:
            return None

        selected_antenna = self.antenna_var.get()
        selected_signals = set(
            sig for sig, var in self.signal_checkbuttons.items() if var.get()
        )

        if not selected_signals:
            messagebox.showwarning("No Signals", "Please select at least one signal.")
            return None

        # Filter
        filtered = {
            'metadata': {},
            'pco': {},
            'pcv': {},
        }

        source_meta = self.antex_data.get('metadata', {})
        source_pco = self.antex_data.get('pco', {})
        source_pcv = self.antex_data.get('pcv', {})

        antenna_keys = sorted(source_meta.keys())
        if selected_antenna != "All":
            antenna_keys = [selected_antenna] if selected_antenna in source_meta else []

        for ant_key in antenna_keys:
            filtered['metadata'][ant_key] = source_meta[ant_key].copy()
            filtered['pco'][ant_key] = {}
            filtered['pcv'][ant_key] = {}

            for sys_name in source_pco.get(ant_key, {}):
                for fc in source_pco[ant_key][sys_name]:
                    if fc in selected_signals:
                        if sys_name not in filtered['pco'][ant_key]:
                            filtered['pco'][ant_key][sys_name] = {}
                        filtered['pco'][ant_key][sys_name][fc] = source_pco[ant_key][sys_name][fc]

            for sys_name in source_pcv.get(ant_key, {}):
                for fc in source_pcv[ant_key][sys_name]:
                    if fc in selected_signals:
                        if sys_name not in filtered['pcv'][ant_key]:
                            filtered['pcv'][ant_key][sys_name] = {}
                        filtered['pcv'][ant_key][sys_name][fc] = source_pcv[ant_key][sys_name][fc]

        return filtered

    def _scan_source_records(self):
        """
        Read the source file once and collect the records the writer has to
        reproduce faithfully:

          * header comments      - every COMMENT before END OF HEADER
          * per-antenna comments - COMMENT lines inside an antenna block
          * per-antenna METH     - the METH / BY / # / DATE content

        Comments are collected by position, not by searching the whole file for
        calibration keywords: a keyword search would drop header comments that
        do not match and move antenna comments into the header.

        Antenna keys are built the same way as in the ANTEX parser
        (`data_io.read_antex_file`) so they line up with the parsed data:
        "<type> <serial>", with a blank/NONE serial becoming "TYPEMEAN".

        Returns:
            (header_comments, antenna_comments, antenna_meth)
        """
        header_comments = []
        antenna_comments = {}
        antenna_meth = {}

        if not self.source_path:
            return header_comments, antenna_comments, antenna_meth

        in_header = True
        current_key = None
        try:
            with open(self.source_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if len(line) < 61:
                        continue
                    label = line[60:].strip()
                    content = line[:60].rstrip()

                    if label == 'END OF HEADER':
                        in_header = False
                    elif label in ('START OF ANTENNA', 'END OF ANTENNA'):
                        current_key = None
                    elif label in ('TYPE / SERIAL NO', 'TYPE / SN'):
                        ant_type = line[0:20].strip()
                        ant_serial = line[20:40].strip()
                        if not ant_serial or ant_serial.upper() == 'NONE':
                            ant_serial = 'TYPEMEAN'
                        current_key = f"{ant_type} {ant_serial}".strip()
                    elif label == 'COMMENT':
                        if in_header:
                            header_comments.append(content)
                        elif current_key:
                            antenna_comments.setdefault(current_key, []).append(content)
                    elif label == 'METH / BY / # / DATE' and current_key:
                        antenna_meth[current_key] = content
        except OSError:
            pass

        return header_comments, antenna_comments, antenna_meth

    def _build_output_comments(self):
        """Header COMMENT lines for the output: the source's own, verbatim.

        The writer appends exactly one note of its own recording that
        ATX-Converter produced the file, so nothing is added here.
        """
        header_comments, _, _ = self._scan_source_records()
        return header_comments

    @staticmethod
    def _compose_preview(lines, head_lines=14, tail_header=10, antenna_lines=48):
        """
        Build a preview that shows the parts a reviewer needs to see.

        Simply printing the first 80 lines is useless for a file like
        igs20.atx: its header carries hundreds of COMMENT lines, so the preview
        never reaches an antenna block - where the METH record and the frequency
        blocks are. This shows the start of the header, then the end of it
        (including the note this program adds), then the first antenna in full,
        with a marker wherever lines were skipped.
        """
        def label_of(line):
            return line[60:].strip() if len(line) > 60 else ''

        end_of_header = next((i for i, l in enumerate(lines)
                              if label_of(l) == 'END OF HEADER'), None)
        first_antenna = next((i for i, l in enumerate(lines)
                              if label_of(l) == 'START OF ANTENNA'), None)

        if end_of_header is None or first_antenna is None:
            out = lines[:80]
            if len(lines) > 80:
                out.append(f"\n... ({len(lines)} total lines)")
            return '\n'.join(out)

        out = []
        header = lines[:end_of_header + 1]
        if len(header) <= head_lines + tail_header:
            out.extend(header)
        else:
            out.extend(header[:head_lines])
            skipped = len(header) - head_lines - tail_header
            out.append(f"{'':.<60}[ {skipped} further header lines not shown ]")
            out.extend(header[-tail_header:])

        # The first antenna block: TYPE, its comments, METH, and the frequency
        # blocks.
        block_end = next((i for i in range(first_antenna, len(lines))
                          if label_of(lines[i]) == 'END OF ANTENNA'), len(lines) - 1)
        block = lines[first_antenna:block_end + 1]
        out.append('')
        if len(block) <= antenna_lines:
            out.extend(block)
        else:
            out.extend(block[:antenna_lines])
            out.append(f"{'':.<60}[ {len(block) - antenna_lines} more lines in this antenna ]")

        n_ant = sum(1 for l in lines if label_of(l) == 'START OF ANTENNA')
        out.append('')
        out.append(f"... ({len(lines)} total lines, {n_ant} antenna(s))")
        return '\n'.join(out)

    def _do_preview(self):
        """Generate preview of the output file."""
        filtered = self._get_filtered_data()
        if not filtered:
            return

        # Write to temp, read first 80 lines. Honor the selected output format
        # so the preview matches what "Convert & Export" will produce.
        import tempfile
        tmp_path = os.path.join(tempfile.gettempdir(), '_pcc_convertor_preview.atx')
        fmt = self.output_format_var.get()
        try:
            comments, ant_comments, ant_meth = self._scan_source_records()
            if "1.4" in fmt:
                write_antex_v14(tmp_path, filtered, comments=comments,
                                antenna_comments=ant_comments, antenna_meth=ant_meth)
            else:
                write_antex_v2(tmp_path, filtered, comments=comments,
                               antenna_comments=ant_comments, antenna_meth=ant_meth)
            with open(tmp_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.read().splitlines()
            preview = self._compose_preview(lines)
        except Exception as e:
            preview = f"Error generating preview:\n{e}"
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass

        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', 'end')
        self.preview_text.insert('1.0', preview)
        self.preview_text.config(state='disabled')

    def _do_convert(self):
        """Perform the conversion and export."""
        filtered = self._get_filtered_data()
        if not filtered:
            return

        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showwarning("No Output Path", "Please specify an output file path.")
            return

        fmt = self.output_format_var.get()

        try:
            comments, ant_comments, ant_meth = self._scan_source_records()
            if "1.4" in fmt:
                write_antex_v14(output_path, filtered, comments=comments,
                                antenna_comments=ant_comments, antenna_meth=ant_meth)
            else:
                write_antex_v2(output_path, filtered, comments=comments,
                               antenna_comments=ant_comments, antenna_meth=ant_meth)

            n_ant = len(filtered['metadata'])
            n_sig = sum(len(fc) for ant in filtered['pco'].values() for fc in ant.values())
            self.status_var.set(f"Exported: {n_ant} antenna(s), {n_sig} signal(s) -> {os.path.basename(output_path)}")
            messagebox.showinfo("Export Complete",
                                f"ANTEX file exported successfully!\n\n"
                                f"File: {output_path}\n"
                                f"Antennas: {n_ant}\n"
                                f"Signals: {n_sig}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")
            self.status_var.set(f"Export failed: {e}")


    def _show_about(self):
        messagebox.showinfo("Information - ATX-Converter",
                            "ATX-Converter\n" + VERSION_TEXT + "\n\n"
                            "Converts GNSS antenna calibration files between\n"
                            "ANTEX v1.4 and ANTEX v2.0 formats, with\n"
                            "antenna and signal filtering.\n\n"
                            "Institut f\u00fcr Erdmessung (IfE)\n"
                            "Leibniz Universit\u00e4t Hannover\n\n"
                            "License: GNU General Public License v3 (GPLv3)\n\n"
                            "Developers:\n"
                            "  Amr Fawzy, M.Sc.\n"
                            "  Dr.-Ing. Johannes Kr\u00f6ger")

    def _show_contact(self):
        _show_ife_contact(self)

    def _show_mailing_list(self):
        """The mailing list dialog, on request, whatever was answered before."""
        if mailing_list is None:
            messagebox.showwarning(
                "IfE software mailing list",
                "This installation is missing mailing_list.py, so the "
                "subscription dialog cannot be shown. Please report it to "
                "the IfE, the Contact button has the address.")
            return
        mailing_list.show_on_request(self, "ATX-Converter")


def main():
    app = PCCConvertorApp()
    if mailing_list is not None:
        mailing_list.maybe_show(app, "ATX-Converter")
    app.mainloop()


if __name__ == "__main__":
    if 'win' in sys.platform:
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
    main()
