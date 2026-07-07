import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageOps, ImageFilter
import xml.etree.ElementTree as ET
import os, sys, math, re

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def cleanup_name(name):
    replacements = {"Sony Computer Entertainment": "SCE", "Electronic Arts": "EA", "Role Playing Game": "RPG"}
    for long, short in replacements.items():
        name = name.replace(long, short)
    return name

def draw_crt_text(draw, pos, text, font, fill=(255,255,255)):
    x, y = pos
    for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
        draw.text((x+ox, y+oy), text, font=font, fill=(0,0,0))
    draw.text((x, y), text, font=font, fill=fill)

def gauge_width(raw_rating, scale=1):
    return 0 if raw_rating is None else int(88 * scale)

def stars_width(rating, scale=1):
    return 0 if rating is None else int(22 * scale) * 5

def player_count(player_str):
    try:
        return min(4, int(max([int(s) for s in player_str.split('-') if s.isdigit()] or [1])))
    except:
        return 1

def player_width(player_str, scale=1):
    p_count = player_count(player_str)
    icon_w = int(9 * scale)
    gap = int(4 * scale)
    return (p_count * icon_w) + ((p_count - 1) * gap)

def rating_width(rating, use_stars, scale=1):
    return stars_width(rating, scale) if use_stars else gauge_width(rating, scale)

def draw_gauge(draw, right_x, y, raw_rating, scale=1):
    gw = gauge_width(raw_rating, scale)
    if gw == 0: return 0
    pct = max(0.0, min(1.0, float(raw_rating)))
    gh = int(12 * scale)
    xs = right_x - gw
    draw.rectangle([xs-3, y-3, xs+gw+3, y+gh+3], outline=(255,255,255,140), width=1)
    col = (255,255,0) if pct>=0.9 else (0,255,0) if pct>=0.7 else (154,205,50) if pct>=0.5 else (255,165,0) if pct>=0.3 else (255,0,0)
    draw.rectangle([xs, y, xs+gw, y+gh], fill=(40,40,40), outline=(190,190,190), width=2)
    if (fw := int(gw * pct)) > 0:
        draw.rectangle([xs, y, xs+fw, y+gh], fill=col)
    return gw

def draw_stars(draw, right_x, y, rating, scale=1):
    sw = stars_width(rating, scale)
    if sw == 0: return 0
    stars = int(float(rating) * 5)
    spacing = int(22 * scale)
    font_size = max(10, int(16 * scale))
    try:
        star_font = ImageFont.truetype(resource_path("DejaVuSans-Bold.ttf"), font_size)
    except Exception:
        star_font = ImageFont.load_default()
    for i in range(5):
        x = right_x - (5 - i) * spacing
        color = (255, 215, 0) if i < stars else (100, 100, 100)
        draw.text((x, y-2), "★", fill=color, font=star_font)
    return sw

def draw_player(draw, right_x, y, player_str, scale=1):
    p_count = player_count(player_str)
    icon_w = int(9 * scale)
    gap = int(4 * scale)
    total_w = (p_count * icon_w) + ((p_count - 1) * gap)
    start_x = right_x - total_w
    for i in range(p_count):
        x = start_x + (i * (icon_w + gap))
        draw.ellipse([x, y, x + icon_w, y + icon_w], fill=(255, 255, 255))
        draw.rectangle([x + 2, y + icon_w + 1, x + icon_w - 2, y + icon_w + 6], fill=(255, 255, 255))
    return total_w

def load_gamelist(xml_path):
    try:
        with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        start = raw.find("<gameList>"); end = raw.rfind("</gameList>")
        root = ET.fromstring(raw[start:end + len("</gameList>")])
        data = {}
        for g in root.findall("game"):
            raw_name = g.findtext("name", "").strip()
            name = raw_name.lower()
            if not name: continue
            path = g.findtext("path", "")
            rom_base = os.path.splitext(os.path.basename(path))[0] if path else ""
            meta = {
                "year": g.findtext("releasedate", "")[:4] or "----",
                "genre": g.findtext("genre", "Unknown"),
                "publisher": g.findtext("publisher", "Unknown"),
                "developer": g.findtext("developer", "Unknown"),
                "rating": g.findtext("rating"),
                "players": g.findtext("players", "1"),
                "description": g.findtext("desc", "No description available."),
                "raw_name": raw_name,
                "rom_base": rom_base,
            }
            data[name] = meta
            if rom_base:
                data[rom_base.lower()] = meta
        return data
    except: return {}

def sanitize_stem(s):
    s = (s or "").strip().lower()
    return re.sub(r'[\/:*?"<>|]', '', s)

def load_media_lookup(folder):
    lookup = {}
    try:
        for f in os.listdir(folder):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                stem = sanitize_stem(os.path.splitext(f)[0])
                lookup[stem] = os.path.join(folder, f)
    except Exception:
        pass
    return lookup

def find_media_image(md_lookup, meta, screenshot_base_name):
    candidates = []
    if meta:
        if meta.get("rom_base"): candidates.append(sanitize_stem(meta["rom_base"]))
        if meta.get("raw_name"): candidates.append(sanitize_stem(meta["raw_name"]))
    candidates.append(sanitize_stem(screenshot_base_name))
    for cand in candidates:
        if cand and cand in md_lookup:
            return md_lookup[cand]
    return None

def _dashed_rect(draw, box, color, width, dash=10, gap=6):
    x0, y0, x1, y1 = box
    corners = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for (xa, ya), (xb, yb) in corners:
        length = math.hypot(xb - xa, yb - ya)
        if length == 0: continue
        dx, dy = (xb - xa) / length, (yb - ya) / length
        pos = 0
        while pos < length:
            seg_end = min(pos + dash, length)
            draw.line([xa + dx*pos, ya + dy*pos, xa + dx*seg_end, ya + dy*seg_end], fill=color, width=width)
            pos += dash + gap

def draw_border(draw, box, style, color, width, radius):
    x0, y0, x1, y1 = box
    if style == "Square":
        draw.rectangle(box, outline=color, width=width)
    elif style == "Dashed":
        _dashed_rect(draw, box, color, width)
    elif style == "Double":
        inset = width + 3
        thin = max(1, width // 2)
        draw.rounded_rectangle(box, radius=radius, outline=color, width=thin)
        draw.rounded_rectangle(
            [x0 + inset, y0 + inset, x1 - inset, y1 - inset],
            radius=max(2, radius - inset), outline=color, width=thin
        )
    elif style == "Glow":
        for i in range(4, 0, -1):
            alpha = int(color[3] * (i / 14))
            glow_color = (*color[:3], max(0, alpha))
            expand = i * 3
            draw.rounded_rectangle(
                [x0 - expand, y0 - expand, x1 + expand, y1 + expand],
                radius=radius + expand, outline=glow_color, width=width
            )
        draw.rounded_rectangle(box, radius=radius, outline=color, width=width)
    else:
        draw.rounded_rectangle(box, radius=radius, outline=color, width=width)

def wrap_text(text, max_width, font, draw):
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        if draw.textlength(test_line, font=font) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def draw_description_box(img, x, y, w, h, description, box_color, border_color, border_width, border_style,
                          corner_radius, shadow, font, text_scale):
    """Draw a description box with wrapped text."""
    if not description or description.strip() == "":
        return
    
    inner_pad = int(12 * text_scale)
    
    meas = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap_text(description, w - (inner_pad * 2), font, meas)
    
    line_height = int(18 * text_scale)
    content_h = len(lines) * line_height + (inner_pad * 2)
    actual_h = min(h, content_h)
    
    radius = max(0, min(corner_radius, w // 2, actual_h // 2))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    
    if shadow:
        d.rounded_rectangle([x-5, y-5, x+w+5, y+actual_h+5], radius=radius+4, fill=(0,0,0,160))
    
    d.rounded_rectangle([x, y, x+w, y+actual_h], radius=radius, fill=box_color)
    draw_border(d, [x, y, x+w, y+actual_h], border_style, border_color, border_width, radius)
    
    img.alpha_composite(overlay)
    
    td = ImageDraw.Draw(img)
    
    text_y = y + inner_pad
    for line in lines:
        if text_y + line_height > y + actual_h:
            break
        draw_crt_text(td, (x + inner_pad, text_y), line, font)
        text_y += line_height

def draw_metadata_bar(img, x, y, w, meta, bar_color, border_color, border_width, border_style,
                       corner_radius, shadow, padding_scale, font, use_stars, text_scale):
    inner_pad = int(12 * text_scale * padding_scale)
    icon_gap = int(10 * text_scale * padding_scale)
    text_gap = int(12 * text_scale * padding_scale)
    v_pad = int(8 * text_scale * padding_scale)

    rw = rating_width(meta.get("rating"), use_stars, text_scale)
    pw = player_width(meta.get("players", "1"), text_scale)
    right_block_w = pw + (icon_gap if rw else 0) + rw

    meas = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    pub = cleanup_name(meta.get("publisher", "Unknown"))
    dev = cleanup_name(meta.get("developer", "Unknown"))
    text = f"{meta['year']} | {meta.get('genre','Unknown')} | {pub if pub == dev else f'{pub}/{dev}'}"

    max_text_w = max(int(50 * text_scale), w - (inner_pad * 2) - right_block_w - text_gap)

    if meas.textlength(text, font=font) > max_text_w:
        while len(text) > 8 and meas.textlength(text + "...", font=font) > max_text_w:
            text = text[:-1]
        text += "..."

    text_w = meas.textlength(text, font=font)
    min_required_w = inner_pad + int(text_w) + text_gap + right_block_w + inner_pad
    if min_required_w > w:
        cx = x + w / 2
        w = int(min_required_w)
        x = int(cx - w / 2)

    text_bbox = meas.textbbox((0, 0), text, font=font)
    text_h = text_bbox[3] - text_bbox[1]
    icon_row_h = max(int(14 * text_scale), int(9 * text_scale) + 4)
    h = max(text_h, icon_row_h) + v_pad * 2

    radius = max(0, min(corner_radius, w // 2, h // 2))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    if shadow:
        d.rounded_rectangle([x-5, y-5, x+w+5, y+h+5], radius=radius+4, fill=(0,0,0,160))

    d.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=bar_color)
    draw_border(d, [x, y, x+w, y+h], border_style, border_color, border_width, radius)

    img.alpha_composite(overlay)
    td = ImageDraw.Draw(img)

    text_y = y + (h - text_h) // 2 - text_bbox[1]
    draw_crt_text(td, (x + inner_pad, text_y), text, font)

    right_edge = x + w - inner_pad
    row_y = y + (h - icon_row_h) // 2

    if use_stars:
        drawn_rw = draw_stars(td, right_edge, row_y, meta.get("rating"), text_scale)
    else:
        drawn_rw = draw_gauge(td, right_edge, row_y, meta.get("rating"), text_scale)

    gap = icon_gap if drawn_rw else 0
    draw_player(td, right_edge - drawn_rw - gap, row_y, meta.get("players", "1"), text_scale)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Console Mode Background Wizard by Hinph")
        self.geometry("680x620")
        self.resizable(False, False)
        
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass

        BG, FG, FIELD, ACCENT, ACCENT_ACTIVE, BORDER = (
            "#1e1f29", "#e8e8f0", "#2a2b38", "#5b8cff", "#4a76e0", "#3a3b4a"
        )

        self.configure(bg=BG)
        style.configure(".", background=BG, foreground=FG, fieldbackground=FIELD, bordercolor=BORDER)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("TkDefaultFont", 9))
        style.configure("TCheckbutton", background=BG, foreground=FG, font=("TkDefaultFont", 9))
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TNotebook", background=BG, bordercolor=BG)
        style.configure("TNotebook.Tab", background=FIELD, foreground=FG, padding=(10, 4), font=("TkDefaultFont", 9))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "#ffffff")])
        style.configure("TButton", background=ACCENT, foreground="#ffffff", padding=3, borderwidth=0, font=("TkDefaultFont", 9))
        style.map("TButton", background=[("active", ACCENT_ACTIVE)])
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=FG, arrowcolor=FG, font=("TkDefaultFont", 9))
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)])
        style.configure("Horizontal.TScale", background=BG, troughcolor=FIELD)
        style.configure("TProgressbar", background=ACCENT, troughcolor=FIELD)
        style.configure("Section.TLabel", font=("TkDefaultFont", 9, "bold"), foreground="#5b8cff")

        self.paths = {"xml": tk.StringVar(), "ss": tk.StringVar(), "md": tk.StringVar(), "out": tk.StringVar()}
        self.path_enabled = {
            "xml": tk.BooleanVar(value=True),
            "ss": tk.BooleanVar(value=True),
            "md": tk.BooleanVar(value=True),
        }

        self.plain_bg = tk.BooleanVar(value=False)
        self.optimize = tk.BooleanVar(value=True)
        self.bg_color = (30, 30, 40, 255)
        self.bar_rgb = (25, 45, 90)
        self.border_color = (255, 255, 255, 220)
        self.desc_rgb = (25, 45, 90)
        self.border_width_map = {"Small": 2, "Medium": 4, "Large": 7}
        self.corner_radius_map = {"Sharp": 0, "Rounded": 10, "Pill": 999}
        self.padding_map = {"Compact": 0.75, "Normal": 1.0, "Spacious": 1.35}
        self.dim_map = {
            "Light (15% dim)": 0.85,
            "Medium (30% dim)": 0.70,
            "Heavy (60% dim)": 0.40,
        }

        self.custom_font = None
        self.desc_custom_font = None
        self.use_stars = tk.BooleanVar(value=False)
        self.bar_shadow = tk.BooleanVar(value=True)
        self.media_shadow = tk.BooleanVar(value=True)
        self.use_description = tk.BooleanVar(value=False)
        self.desc_shadow = tk.BooleanVar(value=True)

        # Initialize all DoubleVar and IntVar BEFORE using them in widgets
        self.text_scale_var = tk.DoubleVar(value=0.9)
        self.bar_w = tk.DoubleVar(value=500)
        self.bar_y = tk.DoubleVar(value=70)
        self.bar_alpha_pct = tk.IntVar(value=82)
        self.desc_w = tk.DoubleVar(value=160)
        self.desc_h = tk.DoubleVar(value=180)
        self.desc_x = tk.DoubleVar(value=20)
        self.desc_y = tk.DoubleVar(value=200)
        self.desc_font_scale = tk.DoubleVar(value=0.8)
        self.media_x = tk.DoubleVar(value=80)
        self.media_y = tk.DoubleVar(value=60)

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=6, pady=6)
        self.notebook = notebook

        # Paths Tab
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Paths")

        for key, label in zip(self.paths.keys(), ['XML File', 'Screenshots', 'Physical Media', 'Output']):
            f = ttk.Frame(tab1); f.pack(fill='x', padx=8, pady=3)
            if key in self.path_enabled:
                ttk.Checkbutton(
                    f, text="", variable=self.path_enabled[key],
                    command=lambda k=key: self.on_path_toggle(k), width=2
                ).pack(side='left', padx=(0, 4))
            ttk.Button(f, text=label, command=lambda k=key: self.pick(k), width=16).pack(side='left', padx=(0, 4))
            ttk.Label(f, textvariable=self.paths[key], relief="sunken", wraplength=380, foreground="#a0a0b0").pack(side='left', fill='x', padx=2)

        # Background Tab
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Background")

        ttk.Label(tab2, text="Background Settings", style="Section.TLabel").pack(anchor='w', padx=8, pady=(8, 4))

        f = ttk.Frame(tab2); f.pack(fill='x', padx=8, pady=2)
        ttk.Checkbutton(f, text="Plain Background", variable=self.plain_bg).pack(side='left', padx=2)
        ttk.Button(f, text="Color", command=self.choose_bg, width=8).pack(side='left', padx=2)
        self.bg_swatch = tk.Label(f, text="  ", bg=self._hex(self.bg_color), relief="raised", width=2)
        self.bg_swatch.pack(side='left', padx=2)

        ttk.Label(tab2, text="Brightness", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(6, 0))
        self.dim_choice = ttk.Combobox(tab2, values=list(self.dim_map.keys()), state="readonly", width=40)
        self.dim_choice.current(1)
        self.dim_choice.pack(padx=8, anchor='w', pady=(0, 2))

        # Metadata Bar Tab
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="Metadata Bar")

        ttk.Label(tab3, text="Bar Style", style="Section.TLabel").pack(anchor='w', padx=8, pady=(8, 4))

        color_row = ttk.Frame(tab3); color_row.pack(fill='x', padx=8, pady=2)
        ttk.Button(color_row, text="Bar", command=self.choose_bar, width=6).pack(side='left', padx=1)
        self.bar_swatch = tk.Label(color_row, text="  ", bg=self._hex((*self.bar_rgb, 255)), relief="raised", width=2)
        self.bar_swatch.pack(side='left', padx=1)
        ttk.Button(color_row, text="Border", command=self.choose_border, width=8).pack(side='left', padx=1)
        self.border_swatch = tk.Label(color_row, text="  ", bg=self._hex(self.border_color), relief="raised", width=2)
        self.border_swatch.pack(side='left', padx=1)

        self.border_strength = ttk.Combobox(tab3, values=["Small", "Medium", "Large"], state="readonly", width=10)
        self.border_style = ttk.Combobox(tab3, values=["Solid", "Double", "Dashed", "Glow"], state="readonly", width=10)
        self.corner_radius_choice = ttk.Combobox(tab3, values=list(self.corner_radius_map.keys()), state="readonly", width=10)
        self.padding_choice = ttk.Combobox(tab3, values=list(self.padding_map.keys()), state="readonly", width=10)

        self.border_strength.current(0)
        self.border_style.current(0)
        self.corner_radius_choice.current(1)
        self.padding_choice.current(0)

        for label, combo, padx_val in [
            ("Border", self.border_strength, 1),
            ("Style", self.border_style, 4),
            ("Radius", self.corner_radius_choice, 4),
            ("Padding", self.padding_choice, 4),
        ]:
            f = ttk.Frame(tab3); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=7).pack(side='left')
            combo.pack(side='left', padx=padx_val)

        ttk.Checkbutton(tab3, text="Shadow", variable=self.bar_shadow).pack(anchor='w', padx=8, pady=3)

        ttk.Label(tab3, text="Transparency", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4, 0))
        trans_row = ttk.Frame(tab3); trans_row.pack(fill='x', padx=8)
        self.bar_alpha_label = ttk.Label(trans_row, text="82%", width=4)
        self.bar_alpha_label.pack(side='right')
        ttk.Scale(
            trans_row, from_=10, to=100, orient="horizontal", variable=self.bar_alpha_pct,
            command=lambda v: self.bar_alpha_label.config(text=f"{int(float(v))}%")
        ).pack(side='left', fill='x', padx=(0, 6))

        ttk.Label(tab3, text="Text Scale", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4, 0))
        ttk.Scale(tab3, from_=0.7, to=1.5, orient="horizontal", variable=self.text_scale_var).pack(fill='x', padx=8)

        ttk.Label(tab3, text="Position & Size", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4, 0))
        for label, var, from_, to_, default in [
            ("Width", self.bar_w, 300, 1000, 500),
            ("Y Pos", self.bar_y, 20, 800, 70),
        ]:
            f = ttk.Frame(tab3); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=7).pack(side='left')
            scale = ttk.Scale(f, from_=from_, to=to_, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            lbl = ttk.Label(f, text=str(int(default)), width=4)
            lbl.pack(side='right')
            scale.config(command=lambda v, l=lbl: l.config(text=str(int(float(v)))))

        ttk.Checkbutton(tab3, text="Star Rating", variable=self.use_stars).pack(anchor='w', padx=8, pady=3)
        ttk.Button(tab3, text="Select Font", command=self.pick_font, width=20).pack(pady=4)

        # Description Tab
        tab_desc = ttk.Frame(notebook)
        notebook.add(tab_desc, text="Description")

        ttk.Checkbutton(tab_desc, text="Enable Description Box", variable=self.use_description).pack(anchor='w', padx=8, pady=(6, 4))

        ttk.Label(tab_desc, text="Description Style", style="Section.TLabel").pack(anchor='w', padx=8, pady=(4, 4))

        color_row_desc = ttk.Frame(tab_desc); color_row_desc.pack(fill='x', padx=8, pady=2)
        ttk.Button(color_row_desc, text="Color", command=self.choose_desc, width=8).pack(side='left', padx=1)
        self.desc_swatch = tk.Label(color_row_desc, text="  ", bg=self._hex((*self.desc_rgb, 255)), relief="raised", width=2)
        self.desc_swatch.pack(side='left', padx=1)
        ttk.Checkbutton(color_row_desc, text="Shadow", variable=self.desc_shadow).pack(side='left', padx=8)
        ttk.Button(color_row_desc, text="Font", command=self.pick_desc_font, width=8).pack(side='left', padx=1)

        ttk.Label(tab_desc, text="Size & Position", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4, 0))
        for label, var, from_, to_, default in [
            ("Width", self.desc_w, 100, 400, 160),
            ("Height", self.desc_h, 80, 400, 180),
            ("X Pos", self.desc_x, 0, 1000, 20),
            ("Y Pos", self.desc_y, 0, 800, 200),
            ("Text Scale", self.desc_font_scale, 0.5, 1.5, 0.8),
        ]:
            f = ttk.Frame(tab_desc); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=10).pack(side='left')
            scale = ttk.Scale(f, from_=from_, to=to_, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            lbl = ttk.Label(f, text=f"{default:.1f}" if "Scale" in label else str(int(default)), width=4)
            lbl.pack(side='right')
            if "Scale" in label:
                scale.config(command=lambda v, l=lbl: l.config(text=f"{float(v):.1f}"))
            else:
                scale.config(command=lambda v, l=lbl: l.config(text=str(int(float(v)))))

        # Physical Media Tab
        tab4 = ttk.Frame(notebook)
        notebook.add(tab4, text="Physical Media")

        ttk.Label(tab4, text="Media Settings", style="Section.TLabel").pack(anchor='w', padx=8, pady=(8, 4))

        ttk.Label(tab4, text="Size", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8)
        self.media_size = ttk.Combobox(tab4, values=["Small", "Medium", "Large"], state="readonly", width=40)
        self.media_size.current(1)
        self.media_size.pack(padx=8, anchor='w', pady=(0, 4))

        ttk.Label(tab4, text="Position", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4, 0))
        for label, var, from_, to_, default in [
            ("X", self.media_x, 0, 1000, 80),
            ("Y", self.media_y, 20, 600, 60),
        ]:
            f = ttk.Frame(tab4); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=7).pack(side='left')
            scale = ttk.Scale(f, from_=from_, to=to_, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            lbl = ttk.Label(f, text=str(int(default)), width=4)
            lbl.pack(side='right')
            scale.config(command=lambda v, l=lbl: l.config(text=str(int(float(v)))))

        ttk.Checkbutton(tab4, text="Shadow", variable=self.media_shadow).pack(anchor='w', padx=8, pady=4)

        # Bottom controls
        bottom = ttk.Frame(self)
        bottom.pack(fill='x', padx=6, pady=6)

        self.res_mode = ttk.Combobox(bottom, values=["CRT (640x480)", "1080p (1920x1080)"], state="readonly", width=14)
        self.res_mode.current(0)
        self.res_mode.pack(side='left', padx=2)
        ttk.Checkbutton(bottom, text="Optimize", variable=self.optimize).pack(side='left', padx=6)
        ttk.Button(bottom, text="GENERATE", command=self.run).pack(side='right', padx=2)

        self.progress = ttk.Progressbar(self, length=670, mode="determinate")
        self.progress.pack(pady=4)

    @staticmethod
    def _hex(rgba):
        return "#%02x%02x%02x" % tuple(rgba[:3])

    def on_path_toggle(self, key):
        if key == "xml":
            state = "normal" if self.path_enabled["xml"].get() else "disabled"
            self.notebook.tab(2, state=state)
            self.notebook.tab(3, state=state)
        elif key == "ss":
            if not self.path_enabled["ss"].get():
                self.plain_bg.set(True)

    def pick(self, key):
        if key == 'xml':
            p = filedialog.askopenfilename(filetypes=[("XML", "*.xml")])
        else:
            p = filedialog.askdirectory()
        if p: self.paths[key].set(p)

    def choose_bg(self):
        c = colorchooser.askcolor(color=self._hex(self.bg_color))[0]
        if c:
            self.bg_color = (*map(int, c), 255)
            self.bg_swatch.config(bg=self._hex(self.bg_color))

    def choose_bar(self):
        c = colorchooser.askcolor(color=self._hex((*self.bar_rgb, 255)))[0]
        if c:
            self.bar_rgb = tuple(map(int, c))
            self.bar_swatch.config(bg=self._hex((*self.bar_rgb, 255)))

    def choose_border(self):
        c = colorchooser.askcolor(color=self._hex(self.border_color))[0]
        if c:
            self.border_color = (*map(int, c), 220)
            self.border_swatch.config(bg=self._hex(self.border_color))

    def choose_desc(self):
        c = colorchooser.askcolor(color=self._hex((*self.desc_rgb, 255)))[0]
        if c:
            self.desc_rgb = tuple(map(int, c))
            self.desc_swatch.config(bg=self._hex((*self.desc_rgb, 255)))

    def pick_font(self):
        path = filedialog.askopenfilename(filetypes=[("Fonts", "*.ttf *.otf")])
        if path:
            self.custom_font = path
            messagebox.showinfo("Font", "Custom metadata font selected")

    def pick_desc_font(self):
        path = filedialog.askopenfilename(filetypes=[("Fonts", "*.ttf *.otf")])
        if path:
            self.desc_custom_font = path
            messagebox.showinfo("Font", "Custom description font selected")

    def run(self):
        if not self.paths['out'].get():
            messagebox.showwarning("Missing", "Please select an Output folder!")
            return

        use_ss = self.path_enabled['ss'].get() and bool(self.paths['ss'].get())
        use_xml = self.path_enabled['xml'].get() and bool(self.paths['xml'].get())
        use_md = self.path_enabled['md'].get() and bool(self.paths['md'].get())
        use_desc = self.use_description.get() and use_xml

        if not use_ss and not self.plain_bg.get():
            messagebox.showwarning(
                "Missing", "Please select a Screenshots folder, or enable Plain Background!"
            )
            return

        if not use_ss and not use_xml:
            messagebox.showwarning(
                "Missing", "Need either Screenshots or an XML file to know which games to generate!"
            )
            return

        is_1080p = "1080p" in self.res_mode.get()
        W, H = (1920, 1080) if is_1080p else (640, 480)

        text_scale = self.text_scale_var.get()
        border_width = self.border_width_map.get(self.border_strength.get(), 2)
        bar_color = (*self.bar_rgb, int(255 * self.bar_alpha_pct.get() / 100))
        desc_color = (*self.desc_rgb, 220)
        corner_radius = int(self.corner_radius_map.get(self.corner_radius_choice.get(), 10) * text_scale)
        padding_scale = self.padding_map.get(self.padding_choice.get(), 0.75)
        bar_shadow = self.bar_shadow.get()
        media_shadow = self.media_shadow.get()
        desc_shadow = self.desc_shadow.get()

        base_font = 19 if is_1080p else 14
        font_size = max(9, int(base_font * text_scale))
        desc_font_size = max(8, int(base_font * self.desc_font_scale.get()))
        font = None
        desc_font = None

        if self.custom_font:
            try: font = ImageFont.truetype(self.custom_font, font_size)
            except: pass

        if not font:
            try: font = ImageFont.truetype(resource_path("DejaVuSans-Bold.ttf"), font_size)
            except: font = ImageFont.load_default()

        if self.desc_custom_font:
            try: desc_font = ImageFont.truetype(self.desc_custom_font, desc_font_size)
            except: desc_font = None

        if not desc_font:
            try: desc_font = ImageFont.truetype(resource_path("DejaVuSans.ttf"), desc_font_size)
            except: desc_font = font

        games = load_gamelist(self.paths['xml'].get()) if use_xml else {}

        if use_ss:
            files = [
                f for f in os.listdir(self.paths['ss'].get())
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            ]
        else:
            seen = set()
            files = []
            for meta in games.values():
                base = meta.get("rom_base") or meta.get("raw_name")
                if base and base.lower() not in seen:
                    seen.add(base.lower())
                    files.append(base + ".png")

        md_lookup = load_media_lookup(self.paths['md'].get()) if use_md else {}
        self.progress["maximum"] = max(1, len(files))

        for i, file in enumerate(files):
            try:
                if self.plain_bg.get() or not use_ss:
                    bg = Image.new("RGBA", (W, H), self.bg_color)
                else:
                    bg = ImageOps.fit(Image.open(os.path.join(self.paths['ss'].get(), file)), (W, H)).convert("RGBA")
                    bg = ImageEnhance.Brightness(bg).enhance(self.dim_map.get(self.dim_choice.get(), 0.70))

                base_name = os.path.splitext(file)[0].lower()
                meta = games.get(base_name) if use_xml else None

                if meta:
                    bar_width = int(self.bar_w.get())
                    bar_width = max(200, min(bar_width, W - 40))
                    x = (W - bar_width) // 2

                    draw_metadata_bar(
                        bg, x, int(self.bar_y.get()), bar_width, meta,
                        bar_color, self.border_color, border_width, self.border_style.get(),
                        corner_radius, bar_shadow, padding_scale,
                        font, self.use_stars.get(), text_scale
                    )

                    if use_desc and meta.get("description"):
                        desc_x = int(self.desc_x.get())
                        desc_y = int(self.desc_y.get())
                        desc_w = int(self.desc_w.get())
                        desc_h = int(self.desc_h.get())

                        draw_description_box(
                            bg, desc_x, desc_y, desc_w, desc_h,
                            meta.get("description"), desc_color, self.border_color,
                            border_width, self.border_style.get(), corner_radius,
                            desc_shadow, desc_font, self.desc_font_scale.get()
                        )

                media_path = find_media_image(md_lookup, meta, base_name) if use_md else None
                if media_path:
                    try:
                        d = Image.open(media_path).convert("RGBA")
                        size = (
                            120 if self.media_size.get() == "Small"
                            else 153 if self.media_size.get() == "Medium"
                            else 204
                        )
                        d.thumbnail((size, size))
                        mx = W - d.width - int(self.media_x.get())
                        my = H - d.height - int(self.media_y.get())

                        if media_shadow:
                            alpha = d.split()[-1]
                            shadow_layer = Image.new("RGBA", d.size, (0, 0, 0, 170))
                            shadow_layer.putalpha(alpha)
                            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(4))
                            shadow_canvas = Image.new("RGBA", bg.size, (0, 0, 0, 0))
                            shadow_canvas.paste(shadow_layer, (mx + 6, my + 6), shadow_layer)
                            bg.alpha_composite(shadow_canvas)

                        bg.alpha_composite(d, (mx, my))
                    except Exception as e:
                        print(f"Could not load physical media image for '{file}': {e}")

                out_path = os.path.join(self.paths['out'].get(), os.path.splitext(file)[0] + "-BG.png")

                if self.optimize.get():
                    bg = bg.convert("P", palette=Image.ADAPTIVE, colors=128)
                    bg.save(out_path, "PNG", optimize=True, compress_level=9)
                else:
                    bg.save(out_path, "PNG", compress_level=6)

                self.progress["value"] = i + 1
                self.update_idletasks()

            except Exception as e:
                print(f"Error {file}: {e}")

        messagebox.showinfo("Success", "All artwork generated!")

if __name__ == "__main__":
    App().mainloop()
