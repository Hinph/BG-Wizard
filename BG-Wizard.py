import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageTk
import xml.etree.ElementTree as ET
import os, sys, math, re

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def cleanup_name(name):
    replacements = {"Sony Computer Entertainment": "SCE", "Electronic Arts": "EA", "Role Playing Game": "RPG"}
    for long, short in replacements.items():
        name = name.replace(long, short)
    return name

def draw_crt_text(draw, pos, text, font, fill=(255,255,255), outline=True):
    x, y = pos
    if outline:
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

def player_width(player_str, scale=1, use_text=False, icon_style="Classic"):
    if use_text or icon_style == "Players as Text":
        return 40
    p_count = player_count(player_str)
    icon_w = int(9 * scale)
    gap = int(4 * scale)
    if icon_style == "Custom Icon":
        icon_w = int(icon_w * 2.0)
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

def draw_stars(draw, right_x, y, rating, scale=1, style="Classic Filled", color=(255, 215, 0), spacing_mult=1.0):
    sw = stars_width(rating, scale)
    if sw == 0: return 0
    stars = int(float(rating) * 5)
    spacing = int(22 * scale * spacing_mult)
    font_size = max(10, int(16 * scale))
    try:
        star_font = ImageFont.truetype(resource_path("DejaVuSans-Bold.ttf"), font_size)
    except Exception:
        star_font = ImageFont.load_default()
    for i in range(5):
        x = right_x - (5 - i) * spacing
        if style == "Outlined (★/☆)":
            ch = "★" if i < stars else "☆"
            fill_c = color if i < stars else (160, 160, 160)
            # Draw outline (black shadow/outline for retro CRT look)
            for ox, oy in [(-1,0),(1,0),(0,-1),(0,1), (-1,-1),(-1,1),(1,-1),(1,1)]:
                draw.text((x+ox, y+oy-2), ch, font=star_font, fill=(0,0,0))
            draw.text((x, y-2), ch, fill=fill_c, font=star_font)
        else:  # Classic Filled (default)
            ch = "★"
            fill_c = color if i < stars else (100, 100, 100)
            # subtle outline for filled too for consistency
            for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                draw.text((x+ox, y+oy-2), ch, font=star_font, fill=(0,0,0))
            draw.text((x, y-2), ch, fill=fill_c, font=star_font)
    return sw

def draw_player(draw, img, right_x, y, player_str, scale=1, use_text=False, icon_style="Classic", custom_icon_path=None):
    if use_text or icon_style == "Players as Text":
        p_count = player_count(player_str)
        text = f"{p_count}P"
        font_size = max(10, int(14 * scale))
        try:
            pfont = ImageFont.truetype(resource_path("DejaVuSans-Bold.ttf"), font_size)
        except:
            pfont = ImageFont.load_default()
        draw.text((right_x - 35, y-2), text, fill=(255,255,255), font=pfont)
        return 40
    p_count = player_count(player_str)
    icon_w = int(9 * scale)
    gap = int(4 * scale)
    total_w = (p_count * icon_w) + ((p_count - 1) * gap)
    start_x = right_x - total_w
    fill = (255, 255, 255)
    if icon_style == "Custom Icon" and custom_icon_path and os.path.exists(custom_icon_path):
        try:
            custom_icon_w = int(icon_w * 2.0)
            picon = Image.open(custom_icon_path).convert("RGBA").resize((custom_icon_w, custom_icon_w), Image.LANCZOS)
            total_w = (p_count * custom_icon_w) + ((p_count - 1) * gap) if p_count > 0 else 0
            start_x = right_x - total_w
            for i in range(p_count):
                x = start_x + (i * (custom_icon_w + gap))
                offset = (custom_icon_w - icon_w) // 2
                img.paste(picon, (x - offset, y - offset), picon)
            return total_w
        except Exception:
            pass
    for i in range(p_count):
        x = start_x + (i * (icon_w + gap))
        if icon_style == "X":
            cx = x + icon_w // 2
            cy = y + icon_w // 2
            r = max(2, icon_w // 2 - 1)
            lw = max(1, int(1.5 * scale))
            draw.line([cx - r, cy - r, cx + r, cy + r], fill=fill, width=lw)
            draw.line([cx - r, cy + r, cx + r, cy - r], fill=fill, width=lw)
        elif icon_style == "Dots":
            r = max(2, icon_w // 3)
            cx = x + icon_w // 2
            cy = y + icon_w // 2
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        elif icon_style == "Circles":
            draw.ellipse([x + 1, y + 1, x + icon_w - 1, y + icon_w - 1], outline=fill, width=max(1, int(1.5 * scale)))
        else:
            draw.ellipse([x, y, x + icon_w, y + icon_w], fill=fill)
            draw.rectangle([x + 2, y + icon_w + 1, x + icon_w - 2, y + icon_w + 6], fill=fill)
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
    return re.sub(r'[/:*?"<>|]', '', s)

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
    if style == "None" or width <= 0:
        return
    if style == "Square":
        draw.rectangle(box, outline=color, width=width)
    elif style == "Dashed":
        _dashed_rect(draw, box, color, width)
    elif style == "Double":
        inset = width + 3
        thin = max(1, width // 2)
        draw.rounded_rectangle(box, radius=radius, outline=color, width=thin)
        draw.rounded_rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset], radius=max(2, radius - inset), outline=color, width=thin)
    elif style == "Double Square":
        inset = width + 3
        thin = max(1, width // 2)
        draw.rectangle(box, outline=color, width=thin)
        draw.rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset], outline=color, width=thin)
    elif style == "Dashed Square":
        _dashed_rect(draw, box, color, width)
    elif style in ["Glow", "Neon", "Emboss"]:
        for i in range(4, 0, -1):
            alpha = int(color[3] * (i / 14)) if len(color) > 3 else 180
            glow_color = (*color[:3], max(0, alpha))
            expand = i * 3
            draw.rounded_rectangle([x0 - expand, y0 - expand, x1 + expand, y1 + expand], radius=radius + expand, outline=glow_color, width=width)
        draw.rounded_rectangle(box, radius=radius, outline=color, width=width)
    else:
        draw.rounded_rectangle(box, radius=radius, outline=color, width=width)

def wrap_text(text, max_width, font, draw):
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

def create_fill_overlay(size, color1, color2=None, gradient_dir="vertical", texture_path=None, pattern=None):
    overlay = Image.new("RGBA", size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    w, h = size
    
    if pattern:
        pattern = str(pattern).lower().strip()
    
    if texture_path and os.path.exists(texture_path):
        try:
            tex = Image.open(texture_path).convert("RGBA")
            tex = tex.resize((w, h), Image.LANCZOS)
            return tex
        except:
            pass
    
    if color2 and gradient_dir:
        if gradient_dir == "vertical":
            sh = max(h, 1)
            strip = Image.new("RGBA", (1, sh), (0, 0, 0, 0))
            sd = ImageDraw.Draw(strip)
            for y in range(sh):
                ratio = y / (sh - 1) if sh > 1 else 0.0
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                a1 = color1[3] if len(color1) > 3 else 255
                a2 = color2[3] if len(color2) > 3 else 255
                a = int(a1 * (1 - ratio) + a2 * ratio)
                sd.point((0, y), fill=(r, g, b, a))
            overlay = strip.resize((w, h), Image.LANCZOS)
        else:
            sw = max(w, 1)
            strip = Image.new("RGBA", (sw, 1), (0, 0, 0, 0))
            sd = ImageDraw.Draw(strip)
            for x in range(sw):
                ratio = x / (sw - 1) if sw > 1 else 0.0
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                a1 = color1[3] if len(color1) > 3 else 255
                a2 = color2[3] if len(color2) > 3 else 255
                a = int(a1 * (1 - ratio) + a2 * ratio)
                sd.point((x, 0), fill=(r, g, b, a))
            overlay = strip.resize((w, h), Image.LANCZOS)
    else:
        d.rectangle([0,0,w,h], fill=color1)
    
    if pattern == "checkerboard":
        tile = 40
        for yy in range(0, h, tile):
            for xx in range(0, w, tile):
                if (yy // tile + xx // tile) % 2 == 0:
                    d.rectangle([xx, yy, xx+tile, yy+tile], fill=color2[:3] if color2 else (color1[0], color1[1], color1[2], 180))
        return overlay
    elif pattern == "dots":
        for yy in range(0, h, 20):
            for xx in range(0, w, 20):
                d.ellipse([xx, yy, xx+8, yy+8], fill=color2[:3] if color2 else (color1[0], color1[1], color1[2], 120))
    elif pattern == "stripes":
        for yy in range(0, h, 30):
            d.rectangle([0, yy, w, yy+12], fill=color2[:3] if color2 else (color1[0], color1[1], color1[2], 100))
    elif pattern == "grid":
        grid_color = color2[:3] if color2 else (color1[0], color1[1], color1[2], 80)
        for i in range(0, w, 25):
            d.line([i, 0, i, h], fill=grid_color, width=1)
        for i in range(0, h, 25):
            d.line([0, i, w, i], fill=grid_color, width=1)
    elif pattern == "noise":
        import random
        noise_color = color2[:3] if color2 else (color1[0], color1[1], color1[2], 60)
        for _ in range(int(w*h*0.02)):
            x = random.randint(0,w-1)
            y = random.randint(0,h-1)
            d.point((x,y), fill=noise_color)
    elif pattern == "horizontal gradient":
        for x in range(w):
            ratio = x / w
            r = int(color1[0] * (1 - ratio) + (color2[0] if color2 else color1[0]) * ratio)
            g = int(color1[1] * (1 - ratio) + (color2[1] if color2 else color1[1]) * ratio)
            b = int(color1[2] * (1 - ratio) + (color2[2] if color2 else color1[2]) * ratio)
            d.line([(x, 0), (x, h)], fill=(r, g, b, color1[3] if len(color1)>3 else 255))
    elif pattern == "diagonal":
        for i in range(-h, w + h, 8):
            d.line([(i, 0), (i + h, h)], fill=color2[:3] if color2 else (color1[0], color1[1], color1[2], 80), width=1)
    elif pattern == "bricks":
        brick_h = 20
        for yy in range(0, h, brick_h):
            offset = (yy // brick_h) % 2 * 25
            for xx in range(-offset, w, 50):
                d.rectangle([xx, yy, xx+48, yy+brick_h-2], outline=color2[:3] if color2 else (color1[0], color1[1], color1[2], 120), width=1)
    elif pattern == "hex":
        import math
        hex_size = 18
        for yy in range(0, h, int(hex_size * 1.5)):
            xoff = (yy // int(hex_size * 1.5)) % 2 * (hex_size * 0.75)
            for xx in range(0, w, int(hex_size * 1.7)):
                cx, cy = xx + xoff, yy + hex_size
                points = []
                for i in range(6):
                    ang = math.radians(60 * i - 30)
                    points.append((cx + hex_size * math.cos(ang), cy + hex_size * math.sin(ang)))
                d.polygon(points, outline=color2[:3] if color2 else (color1[0], color1[1], color1[2], 90), width=1)
    
    elif pattern == "scanlines":
        scan_col = tuple(color2[:3]) + (70,) if color2 and len(color2) > 2 else (180, 180, 200, 70)
        for yy in range(0, h, 3):
            d.line([(0, yy), (w, yy)], fill=scan_col, width=1)
    elif pattern == "crosshatch":
        hatch_col = tuple(color2[:3]) + (60,) if color2 and len(color2) > 2 else (200, 200, 180, 60)
        for i in range(-h, w + h, 28):
            d.line([(i, 0), (i + h, h)], fill=hatch_col, width=1)
            d.line([(i, h), (i + h, 0)], fill=hatch_col, width=1)
    elif pattern == "waves":
        wave_col = tuple(color2[:3]) + (55,) if color2 and len(color2) > 2 else (160, 170, 220, 55)
        for yy in range(0, h, 7):
            pts = [(xx, yy + int(4 * math.sin((xx + yy * 0.6) / 14.0))) for xx in range(0, w + 1, 6)]
            if len(pts) > 1:
                d.line(pts, fill=wave_col, width=1)
    elif pattern == "lattice":
        lat_col = tuple(color2[:3]) + (45,) if color2 and len(color2) > 2 else (120, 120, 140, 45)
        step = 22
        for yy in range(0, h, step):
            for xx in range(0, w, step):
                d.rectangle([xx + 3, yy + 3, xx + step - 3, yy + step - 3], outline=lat_col, width=1)
    
    return overlay

def draw_rounded_with_fill(img, box, fill_img, radius, border_color=None, border_width=0, border_style="Solid"):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    
    fill_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fill_layer.paste(fill_img.resize((w, h), Image.LANCZOS), (0, 0), mask)
    
    temp = Image.new("RGBA", img.size, (0, 0, 0, 0))
    temp.paste(fill_layer, (x0, y0), fill_layer)
    img.alpha_composite(temp)
    
    if border_color and border_width > 0:
        d = ImageDraw.Draw(img)
        draw_border(d, box, border_style, border_color, border_width, radius)

def draw_description_box(img, x, y, w, h, description, box_color, border_color, border_width, border_style, 
                         corner_radius, shadow, font, text_scale, gradient=False, color2=None, texture=None, pattern=None, text_outline=True, text_color=(255,255,255)):
    if not description or description.strip() == "":
        return
    inner_pad = int(12 * text_scale)
    meas = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap_text(description, w - (inner_pad * 2), font, meas)
    line_height = int(18 * text_scale)
    content_h = len(lines) * line_height + (inner_pad * 2)
    actual_h = min(h, content_h)
    
    if lines and meas.textlength(lines[-1], font=font) > w - (inner_pad * 2) - 20:
        last_line = lines[-1]
        while last_line and meas.textlength(last_line + "...", font=font) > w - (inner_pad * 2):
            last_line = last_line[:-1].strip()
        lines[-1] = last_line + "..."

    radius = max(0, min(corner_radius, w // 2, actual_h // 2))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    
    if shadow:
        shadow_layer = Image.new("RGBA", img.size, (0,0,0,0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.rounded_rectangle([x+6, y+6, x+w+6, y+actual_h+6], radius=radius+3, fill=(0,0,0,110))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(5))
        img.alpha_composite(shadow_layer)
    
    fill_color1 = box_color
    fill_color2 = color2 or (*[int(c*0.7) for c in box_color[:3]], box_color[3]) 
    grad_dir = "vertical" if gradient else None
    fill_overlay = create_fill_overlay((w, actual_h), fill_color1, fill_color2, grad_dir, texture, pattern)
    
    draw_rounded_with_fill(overlay, [x, y, x+w, y+actual_h], fill_overlay, radius, border_color, border_width, border_style)
    
    img.alpha_composite(overlay)
    
    td = ImageDraw.Draw(img)
    text_y = y + inner_pad
    for line in lines:
        if text_y + line_height > y + actual_h:
            break
        draw_crt_text(td, (x + inner_pad, text_y), line, font, fill=text_color, outline=text_outline)
        text_y += line_height

def draw_metadata_bar(img, x, y, w, meta, bar_color, border_color, border_width, border_style, 
                      corner_radius, shadow, padding_scale, font, use_stars, text_scale, 
                      gradient=False, color2=None, texture=None, pattern=None, text_outline=True, 
                      vertical=False, use_player_text=False, bar_x_var=None, bar_y_var=None,
                      text_color=(255,255,255), custom_font_path=None, vertical_labels=False,
                      player_icon_style="Classic", bar_height=None, custom_player_icon_path=None,
                      display_rating_as_text=False, star_style="Classic Filled", star_color=(255, 215, 0),
                      star_spacing_mult=1.0, vertical_player_gap_mult=1.0):
    main_font_size = max(9, int(13 * text_scale))
    font_path = custom_font_path if (custom_font_path and os.path.exists(custom_font_path)) else resource_path("DejaVuSans-Bold.ttf")
    try:
        main_font = ImageFont.truetype(font_path, main_font_size)
    except Exception:
        main_font = ImageFont.load_default()
    
    inner_pad = int(12 * text_scale * padding_scale)
    icon_gap = int(10 * text_scale * padding_scale)
    text_gap = int(12 * text_scale * padding_scale)
    v_pad = int(8 * text_scale * padding_scale)
    raw_r = meta.get("rating")
    if display_rating_as_text and raw_r:
        rw = int(55 * text_scale)
    else:
        rw = rating_width(raw_r, use_stars, text_scale)
    pw = player_width(meta.get("players", "1"), text_scale, use_player_text, player_icon_style)
    right_block_w = pw + (icon_gap if rw else 0) + rw
    
    meas = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    pub = cleanup_name(meta.get("publisher", "Unknown"))
    dev = cleanup_name(meta.get("developer", "Unknown"))
    year = meta.get("year", "----")
    genre = meta.get("genre", "Unknown")
    players_raw = meta.get("players", "1") or "1"
    players_display = f"{players_raw} Players"
    
    if vertical:
        if vertical_labels:
            # Two column layout for nice alignment
            labels = ["Year:", "Genre:", "Publisher:", "Developer:"]
            values = [year, genre, pub, dev]
            # measure max label width
            max_label_w = 0
            label_widths = []
            for lab in labels:
                tw = meas.textlength(lab, font=main_font)
                label_widths.append(tw)
                if tw > max_label_w:
                    max_label_w = tw
            value_start_x = inner_pad + max_label_w + int(8 * text_scale)
            text_lines_for_height = labels  # for height calc
        else:
            text_lines = [
                year,
                genre,
                pub,
                dev,
            ]
            if use_player_text:
                text_lines.append(players_display)
            text_lines_for_height = text_lines
        # Dynamic width
        max_text_w = 0
        if vertical_labels:
            for i, (lab, val) in enumerate(zip(labels, values)):
                tw = label_widths[i] + int(8 * text_scale) + meas.textlength(val, font=main_font)
                if tw > max_text_w:
                    max_text_w = tw
        else:
            for line in text_lines_for_height:
                tw = meas.textlength(line, font=main_font)
                if tw > max_text_w:
                    max_text_w = tw
        rw = rating_width(meta.get("rating"), use_stars, text_scale) if meta.get("rating") else 0
        content_w = max(max_text_w, rw)
        bar_w = content_w + inner_pad * 2 + int(6 * text_scale)
        w = max(140, int(bar_w))
        try:
            bbox = meas.textbbox((0, 0), "Ay", font=main_font)
            lh = bbox[3] - bbox[1] + int(5 * text_scale)
        except:
            lh = int(20 * text_scale)
        line_height = max(16, int(lh))
        extra_rating = int(32 * text_scale)
        if vertical_labels and meta.get("rating"):
            extra_rating += int(14 * text_scale)
        if player_icon_style != "Players as Text" and meta.get("players"):
            extra_rating += int(26 * text_scale)  # more spacing
        h = len(text_lines_for_height) * line_height + inner_pad * 2 + extra_rating
        x = bar_x_var.get() if bar_x_var else x
        y = bar_y_var.get() if bar_y_var else y
    else:
        players = f"{player_count(meta.get('players', '1'))}P"
        text_lines = [
            f"{year}",
            f"{genre}",
            f"{pub}/{dev}",
            players
        ]
        text = f"{year} | {genre} | {pub if pub == dev else f'{pub}/{dev}'}"
        max_text_w = max(int(50 * text_scale), w - (inner_pad * 2) - right_block_w - text_gap)
        if meas.textlength(text, font=main_font) > max_text_w:
            while len(text) > 8 and meas.textlength(text + "...", font=main_font) > max_text_w:
                text = text[:-1]
            text += "..."
        text_w = meas.textlength(text, font=main_font)
        min_required_w = inner_pad + int(text_w) + text_gap + right_block_w + inner_pad
        if min_required_w > w:
            cx = x + w / 2
            w = int(min_required_w)
            x = int(cx - w / 2)
        text_bbox = meas.textbbox((0, 0), text, font=main_font)
        text_h = text_bbox[3] - text_bbox[1]
        icon_row_h = max(int(14 * text_scale), int(9 * text_scale) + 4)
        h = max(text_h, icon_row_h) + v_pad * 2
    
    if bar_height is not None:
        try:
            min_h = int(float(bar_height) * max(0.8, float(text_scale)))
            h = max(h, min_h)
        except:
            pass
    
    radius = max(0, min(corner_radius, w // 2, h // 2))
    
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    
    if shadow:
        shadow_layer = Image.new("RGBA", img.size, (0,0,0,0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.rounded_rectangle([x+5, y+5, x+w+5, y+h+5], radius=radius+4, fill=(0,0,0,130))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(shadow_layer)
    
    fill_color1 = bar_color
    fill_color2 = color2 or (*[int(c*0.6) for c in bar_color[:3]], bar_color[3])
    grad_dir = "vertical" if gradient else None
    fill_overlay = create_fill_overlay((w, h), fill_color1, fill_color2, grad_dir, texture, pattern)
    
    draw_rounded_with_fill(overlay, [x, y, x+w, y+h], fill_overlay, radius, border_color, border_width, border_style)
    
    img.alpha_composite(overlay)
    
    td = ImageDraw.Draw(img)
    if vertical:
        text_y = y + inner_pad
        if vertical_labels:
            for i, (lab, val) in enumerate(zip(labels, values)):
                # label
                draw_crt_text(td, (x + inner_pad, text_y), lab, main_font, fill=text_color, outline=text_outline)
                # value aligned
                draw_crt_text(td, (x + value_start_x, text_y), val, main_font, fill=text_color, outline=text_outline)
                text_y += line_height
        else:
            for line in text_lines:
                draw_crt_text(td, (x + inner_pad, text_y), line, main_font, fill=text_color, outline=text_outline)
                text_y += line_height
        # Rating
        row_y = text_y + int(8 * text_scale)
        center_x = x + w // 2
        if meta.get("rating"):
            if display_rating_as_text:
                rt = f"{int(float(meta.get('rating', 0)) * 100)}%"
                try:
                    rfont_size = max(8, int(10 * text_scale))
                    rfont = ImageFont.truetype(font_path, rfont_size)
                except Exception:
                    rfont = main_font
                tw = meas.textlength(rt, font=rfont) if 'meas' in locals() else 50
                draw_crt_text(td, (center_x - tw // 2, row_y), rt, rfont, fill=text_color, outline=text_outline)
            else:
                if use_stars:
                    sw = stars_width(meta.get("rating"), text_scale)
                    draw_stars(td, center_x + sw // 2, row_y, meta.get("rating"), text_scale, style=star_style, color=star_color, spacing_mult=star_spacing_mult)
                else:
                    gw = gauge_width(meta.get("rating"), text_scale)
                    draw_gauge(td, center_x + gw // 2, row_y, meta.get("rating"), text_scale)
        # Player icons with MORE spacing
        if player_icon_style != "Players as Text":
            p_y = row_y + int(26 * text_scale * vertical_player_gap_mult)
            p_str = meta.get("players", "1")
            pw = player_width(p_str, text_scale, use_text=(player_icon_style == "Players as Text"), icon_style=player_icon_style)
            draw_player(td, img, center_x + pw // 2, p_y, p_str, text_scale, use_text=False, icon_style=player_icon_style, custom_icon_path=custom_player_icon_path)
    else:
        text_y = y + (h - text_h) // 2 - text_bbox[1] if 'text' in locals() else y + inner_pad
        if 'text' in locals():
            draw_crt_text(td, (x + inner_pad, text_y), text, main_font, fill=text_color, outline=text_outline)
        right_edge = x + w - inner_pad
        row_y = y + (h - icon_row_h) // 2
        if display_rating_as_text and meta.get("rating"):
            rt = f"{int(float(meta.get('rating', 0)) * 100)}%"
            try:
                rfont_size = max(8, int(10 * text_scale))
                rfont = ImageFont.truetype(font_path, rfont_size)
            except Exception:
                rfont = main_font
            tw = meas.textlength(rt, font=rfont) if 'meas' in locals() else 45
            draw_crt_text(td, (right_edge - tw, row_y - 2), rt, rfont, fill=text_color, outline=text_outline)
            drawn_rw = tw
        elif use_stars:
            drawn_rw = draw_stars(td, right_edge, row_y, meta.get("rating"), text_scale, style=star_style, color=star_color, spacing_mult=star_spacing_mult)
        else:
            drawn_rw = draw_gauge(td, right_edge, row_y, meta.get("rating"), text_scale)
        gap = icon_gap if drawn_rw else 0
        draw_player(td, img, right_edge - drawn_rw - gap, row_y, meta.get("players", "1"), text_scale, use_text=(player_icon_style == "Players as Text"), icon_style=player_icon_style, custom_icon_path=custom_player_icon_path)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BG Wizard by Hinph")
        self.geometry("1024x720")
        self.resizable(True, True)
        self.minsize(980, 680)
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
        style.configure("DarkBlue.TButton", background="#1e5a8a", foreground="#ffffff", padding=3, borderwidth=0, font=("TkDefaultFont", 9))
        style.map("DarkBlue.TButton", background=[("active", "#163d5e")])

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "icon.png")
            if not os.path.exists(icon_path):
                icon_path = resource_path("icon.png")
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
            else:
                icon_img = Image.new("RGBA", (64, 64), (25, 25, 35, 255))
                idraw = ImageDraw.Draw(icon_img)
                idraw.rounded_rectangle([6, 6, 58, 40], radius=5, fill=(60, 120, 255), outline=(180, 210, 255), width=2)
                idraw.rectangle([12, 12, 52, 34], fill=(15, 20, 35))
                for y in range(15, 33, 3):
                    idraw.line([(12, y), (52, y)], fill=(35, 45, 70), width=1)
                idraw.ellipse([20, 44, 28, 52], fill=(80, 220, 120))
                idraw.ellipse([36, 44, 44, 52], fill=(255, 210, 80))
                idraw.rectangle([48, 46, 56, 50], fill=(200, 80, 80))
            icon_photo = ImageTk.PhotoImage(icon_img)
            self.iconphoto(True, icon_photo)
            self._icon_ref = icon_photo
        except Exception as e:
            print("Icon load warning:", e)

        self.paths = {"xml": tk.StringVar(), "ss": tk.StringVar(), "md": tk.StringVar(), "out": tk.StringVar(), "roms": tk.StringVar(), "optional_media": tk.StringVar()}
        self.path_enabled = {
            "xml": tk.BooleanVar(value=True),
            "ss": tk.BooleanVar(value=True),
            "md": tk.BooleanVar(value=True),
            "roms": tk.BooleanVar(value=False),
            "optional_media": tk.BooleanVar(value=True),
        }
        self.plain_bg = tk.BooleanVar(value=False)
        self.use_custom_bg = tk.BooleanVar(value=False)
        self.custom_bg_image = None
        self.bg_image_mode = tk.StringVar(value="Stretch to Fill")
        self.optimize = tk.BooleanVar(value=True)
        self.bg_color = (30, 30, 40, 255)
        self.bar_rgb = (25, 45, 90)
        self.bar_color2 = (35, 55, 105, 255)
        self.desc_color2 = (35, 55, 105, 255)
        self.border_color = (255, 255, 255, 220)
        self.desc_rgb = (25, 45, 90)
        self.desc_border_color = (255, 255, 255, 220)
        self.desc_text_color = (255, 255, 255)
        self.text_color = (255, 255, 255)
        self.border_width_map = {"Very Thin": 1, "Small": 2, "Medium": 4, "Large": 7}
        self.corner_radius_map = {"Sharp": 0, "Slight": 4, "Rounded": 10, "Strong": 20, "Pill": 999}
        self.padding_map = {"Compact": 0.75, "Normal": 1.0, "Spacious": 1.35}
        self.dim_map = {
            "None (0% dim)": 1.00,
            "Light (15% dim)": 0.85,
            "Medium (30% dim)": 0.70,
            "Heavy (60% dim)": 0.40,
        }
        self.custom_font = None
        self.desc_custom_font = None
        self.use_stars = tk.BooleanVar(value=False)  # False = stars (default). Checkbox checked = use gauge instead
        self.display_rating_as_text = tk.BooleanVar(value=False)
        self.star_style = tk.StringVar(value="Classic Filled")
        self.star_color = (255, 215, 0)
        self.star_spacing_mult = tk.DoubleVar(value=1.0)  # NEW: star spacing control
        self.vertical_player_gap_mult = tk.DoubleVar(value=1.15)  # NEW: extra gap in vertical between rating & players
        self.bar_shadow = tk.BooleanVar(value=True)
        self.media_shadow = tk.BooleanVar(value=True)
        self.use_description = tk.BooleanVar(value=False)
        self.desc_shadow = tk.BooleanVar(value=True)
        self.text_shadow = tk.BooleanVar(value=True)
        self.use_player_text = tk.BooleanVar(value=False)
        self.bar_vertical = tk.BooleanVar(value=False)
        self.vertical_labels = tk.BooleanVar(value=False)
        self.bg_mosaic = tk.BooleanVar(value=False)
        self.bg_gradient = tk.BooleanVar(value=False)
        self.bar_gradient = tk.BooleanVar(value=False)
        self.desc_gradient = tk.BooleanVar(value=False)
        self.bg_color2 = (50, 50, 70, 255)
        self.bar_texture = None
        self.desc_texture = None
        self.bg_pattern = tk.StringVar(value="None")
        self.bar_pattern = tk.StringVar(value="None")
        self.desc_pattern = tk.StringVar(value="None")
        self.desc_border_strength = tk.StringVar(value="Very Thin")
        self.desc_border_style = tk.StringVar(value="Solid")
        self.desc_corner_radius_choice = tk.StringVar(value="Slight")
        self.desc_text_outline = tk.BooleanVar(value=True)
        self.additional_image = None
        self.additional_scale = tk.DoubleVar(value=0.6)
        self.additional_x = tk.DoubleVar(value=100)
        self.additional_y = tk.DoubleVar(value=100)
        self.additional_shadow = tk.BooleanVar(value=False)
        self.additional_alpha = tk.IntVar(value=100)
        self.enable_additional2 = tk.BooleanVar(value=False)
        self.additional2_image = None
        self.additional2_scale = tk.DoubleVar(value=0.5)
        self.additional2_x = tk.DoubleVar(value=200)
        self.additional2_y = tk.DoubleVar(value=150)
        self.additional2_shadow = tk.BooleanVar(value=False)
        self.additional2_alpha = tk.IntVar(value=80)
        self.enable_optional_media = tk.BooleanVar(value=False)
        self.opt_media_x = tk.DoubleVar(value=30)
        self.opt_media_y = tk.DoubleVar(value=30)
        self.opt_media_shadow = tk.BooleanVar(value=True)
        self.opt_media_alpha = tk.IntVar(value=90)
        self.bar_x_var = tk.DoubleVar(value=0)
        self.bar_y_var = tk.DoubleVar(value=80)
        self.bar_height_var = tk.DoubleVar(value=40)
        self.player_icon_style = tk.StringVar(value="Classic")
        self.custom_player_icon = None

        self.layer_order = ["additional", "additional2", "optional_media", "media", "metadata", "description"]

        self.text_scale_var = tk.DoubleVar(value=1.0)
        self.bar_w = tk.DoubleVar(value=700)
        self.bar_y = tk.DoubleVar(value=60)
        self.bar_alpha_pct = tk.IntVar(value=82)
        self.desc_w = tk.DoubleVar(value=320)
        self.desc_h = tk.DoubleVar(value=220)
        self.desc_x = tk.DoubleVar(value=40)
        self.desc_y = tk.DoubleVar(value=280)
        self.desc_font_scale = tk.DoubleVar(value=1.0)
        self.desc_alpha_pct = tk.IntVar(value=85)
        self.hide_metadata = tk.BooleanVar(value=False)
        self.naming_mode = tk.StringVar(value="superstation")
        self.custom_suffix = tk.StringVar(value="-BG")
        self.media_x = tk.DoubleVar(value=40)
        self.media_y = tk.DoubleVar(value=40)
        self.media_alpha = tk.IntVar(value=100)
        self.media_custom_size = tk.DoubleVar(value=168)
        self.opt_media_custom_size = tk.DoubleVar(value=168)

        self.current_res = "CRT (640x480)"
        self.res_mode = None

        top_bar = ttk.Frame(self)
        top_bar.pack(fill='x', padx=6, pady=4)

        style = ttk.Style(self)
        style.configure("BigGreen.TButton", background="#2e7d32", foreground="white", font=("TkDefaultFont", 10, "bold"), padding=6)
        style.map("BigGreen.TButton", background=[("active", "#1b5e20")])

        self.generate_btn = ttk.Button(top_bar, text="GENERATE ALL", command=self.run, style="BigGreen.TButton")
        self.generate_btn.pack(side='right', padx=6)

        self.progress = ttk.Progressbar(top_bar, length=420, mode="determinate")
        self.progress.pack(side='left', padx=6, fill='x', expand=True)

        self.res_mode = ttk.Combobox(top_bar, values=["CRT (640x480)", "720p (1280x720)"], state="readonly", width=18)
        self.res_mode.current(0)
        self.res_mode.pack(side='left', padx=4)
        self.res_mode.bind("<<ComboboxSelected>>", self.on_res_change)
        ttk.Checkbutton(top_bar, text="Optimize", variable=self.optimize).pack(side='left', padx=4)

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=6, pady=2)
        self.notebook = notebook

        self.create_paths_tab()
        self.create_background_tab()
        self.create_metadata_tab()
        self.create_description_tab()
        self.create_media_tab()
        self.create_optional_media_tab()
        self.create_additional_tab()
        self.create_preview_tab()

        desc_frame = ttk.Frame(self)
        desc_frame.pack(fill='x', padx=6, pady=2)
        self.tab_desc_label = ttk.Label(desc_frame, text="", wraplength=680, font=("TkDefaultFont", 7), foreground="#a0a0b0")
        self.tab_desc_label.pack(side='left')
        self.notebook.bind("<<NotebookTabChanged>>", self.update_tab_description)

        self.apply_res_defaults()
        self.update_preview()

    def on_res_change(self, event=None):
        self.apply_res_defaults()
        self.update_preview()

    def get_current_res(self):
        return "720p" if "720p" in self.res_mode.get() else "CRT"

    def apply_res_defaults(self):
        is_720p = self.get_current_res() == "720p"
        W = 1280 if is_720p else 640
        H = 720 if is_720p else 480
        
        bar_w = min(750 if is_720p else 500, W - 80)
        self.bar_w.set(bar_w)
        self.bar_x_var.set( (W - bar_w) // 2 )
        self.bar_y_var.set( max(25, int(H * 0.055)) )
        
        if is_720p:
            self.desc_w.set(380)
            self.desc_h.set(240)
            self.desc_x.set(50)
            self.desc_y.set(280)
            self.media_x.set(50)
            self.media_y.set(50)
            self.additional_x.set(160)
            self.additional_y.set(120)
            self.text_scale_var.set(1.15)
            self.desc_font_scale.set(1.1)
        else:
            self.desc_w.set(280)
            self.desc_h.set(200)
            self.desc_x.set(30)
            self.desc_y.set(220)
            self.media_x.set(30)
            self.media_y.set(30)
            self.additional_x.set(80)
            self.additional_y.set(80)
            self.text_scale_var.set(1.0)
            self.desc_font_scale.set(0.95)

    def create_paths_tab(self):
        tab1 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="Paths")
        ttk.Label(tab1, text="Select folders and files.", style="Section.TLabel").pack(anchor='w', padx=8, pady=4)
        for key, label in zip(['xml', 'ss', 'md', 'out'], ['XML File (gamelist.xml)', 'Background/Screenshot Folder', 'Physical Media Art Folder', 'Save Images to:']):
            f = ttk.Frame(tab1); f.pack(fill='x', padx=8, pady=3)
            ttk.Button(f, text=label, command=lambda k=key: self.pick(k), width=28).pack(side='left', padx=(0, 6))
            ttk.Label(f, textvariable=self.paths[key], relief="sunken", wraplength=380, foreground="#a0a0b0").pack(side='left', fill='x', padx=2)
            # Checkbox removed here
        
        f = ttk.Frame(tab1); f.pack(fill='x', padx=8, pady=6)
        ttk.Label(f, text="Optional Media Folder (extra images; titlescreens, miximages, boxart, fanart, etc...):", style="Section.TLabel").pack(anchor='w')
        ttk.Button(f, text="Select Optional Media Folder", command=lambda: self.pick('optional_media'), width=28).pack(side='left', padx=(0, 6))
        self.opt_media_path_label = ttk.Label(f, textvariable=self.paths['optional_media'], relief="sunken", wraplength=380, foreground="#a0a0b0")
        self.opt_media_path_label.pack(side='left', fill='x', padx=2)
        # Checkbox removed here

        f = ttk.Frame(tab1); f.pack(fill='x', padx=8, pady=12)
        ttk.Label(f, text="Generate from games folder. Use only if you are not using a gamelist.xml file (Metadata unavailable, use exact matching names for roms and image files):", style="Section.TLabel").pack(anchor='w')
        ttk.Button(f, text="Select Games Folder", command=lambda: self.pick('roms'), width=28, style="DarkBlue.TButton").pack(side='left', padx=(0, 6))
        ttk.Label(f, textvariable=self.paths['roms'], relief="sunken", wraplength=380, foreground="#a0a0b0").pack(side='left', fill='x', padx=2)
        # Checkbox removed here

        naming_frame = ttk.LabelFrame(tab1, text="Output File Naming Format", padding=6)
        naming_frame.pack(fill='x', padx=8, pady=8)
        ttk.Radiobutton(naming_frame, text="Superstation format:  [filename]-BG.png", variable=self.naming_mode, value="superstation", command=self.update_preview).pack(anchor='w', padx=4)
        ttk.Radiobutton(naming_frame, text="ES-DE format:  [filename].png", variable=self.naming_mode, value="esde", command=self.update_preview).pack(anchor='w', padx=4)
        custom_row = ttk.Frame(naming_frame); custom_row.pack(fill='x', pady=2, padx=4)
        ttk.Radiobutton(custom_row, text="Custom suffix (e.g. -art or -overlay):", variable=self.naming_mode, value="custom", command=self.update_preview).pack(side='left')
        self.custom_suffix_entry = ttk.Entry(custom_row, textvariable=self.custom_suffix, width=18)
        self.custom_suffix_entry.pack(side='left', padx=6)
        ttk.Label(custom_row, text="→ filename + suffix + .png   (enter including - or . if wanted)", foreground="#888", font=("TkDefaultFont", 7)).pack(side='left', padx=4)

        ttk.Button(tab1, text="Reset All Settings to Defaults", command=self.reset_defaults, style="TButton").pack(pady=10)

    def create_background_tab(self):
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab2, text="Background")
        ttk.Label(tab2, text="Background & Dimming", style="Section.TLabel").pack(anchor='w', padx=8, pady=(8, 4))
        f = ttk.Frame(tab2); f.pack(fill='x', padx=8, pady=4)
        ttk.Checkbutton(f, text="Use Plain or Pattern Background", variable=self.plain_bg).pack(side='left', padx=4)
        ttk.Button(f, text="Primary Color", command=self.choose_bg, width=12).pack(side='left', padx=2)
        self.bg_swatch = tk.Label(f, text=" ", bg=self._hex(self.bg_color), relief="raised", width=3, height=1)
        self.bg_swatch.pack(side='left', padx=2)
        ttk.Button(f, text="Secondary Color", command=self.choose_bg2, width=10).pack(side='left', padx=2)
        self.bg2_swatch = tk.Label(f, text=" ", bg=self._hex(self.bg_color2), relief="raised", width=3, height=1)
        self.bg2_swatch.pack(side='left', padx=2)
        
        pat_frame = ttk.Frame(tab2); pat_frame.pack(fill='x', padx=8, pady=4)
        ttk.Label(pat_frame, text="Background Pattern:").pack(side='left', padx=4)
        self.bg_pattern_combo = ttk.Combobox(pat_frame, textvariable=self.bg_pattern, 
                                           values=["None", "Gradient", "Horizontal Gradient", "Diagonal", "Checkerboard", "Dots", "Stripes", "Grid", "Noise", "Bricks", "Hex", "Scanlines", "Crosshatch", "Lattice"], state="readonly", width=18)
        self.bg_pattern_combo.pack(side='left', padx=4)

        custom_bg_frame = ttk.LabelFrame(tab2, text="Custom Background Image (overrides Screenshots/Plain)", padding=6)
        custom_bg_frame.pack(fill='x', padx=8, pady=6)
        ttk.Checkbutton(custom_bg_frame, text="Use Custom Background Image", variable=self.use_custom_bg, command=self.update_preview).pack(anchor='w', padx=2)
        btn_row = ttk.Frame(custom_bg_frame); btn_row.pack(fill='x', pady=2)
        ttk.Button(btn_row, text="Select BG Image (PNG/JPG)", command=self.load_custom_bg, width=24).pack(side='left', padx=2)
        self.custom_bg_label = ttk.Label(btn_row, text="No image selected", foreground="#a0a0b0", width=40)
        self.custom_bg_label.pack(side='left', padx=4)
        mode_row = ttk.Frame(custom_bg_frame); mode_row.pack(fill='x', pady=2)
        ttk.Label(mode_row, text="Image Mode:").pack(side='left', padx=2)
        self.bg_image_mode_combo = ttk.Combobox(mode_row, textvariable=self.bg_image_mode,
                                                values=["Stretch to Fill", "Zoom to Cover (crop)", "Original Size (centered)", "Tile"], 
                                                state="readonly", width=22)
        self.bg_image_mode_combo.pack(side='left', padx=4)
        self.bg_image_mode_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Label(tab2, text="Screenshot / Custom BG Dimming", font=("TkDefaultFont", 9)).pack(anchor='w', padx=8, pady=(8, 2))
        self.dim_choice = ttk.Combobox(tab2, values=list(self.dim_map.keys()), state="readonly", width=38)
        self.dim_choice.current(1)
        self.dim_choice.pack(padx=8, pady=2, anchor='w')

    def create_metadata_tab(self):
        tab3 = ttk.Frame(self.notebook)
        self.notebook.add(tab3, text="Metadata Bar")
        ttk.Label(tab3, text="Metadata Bar Settings", style="Section.TLabel").pack(anchor='w', padx=8, pady=(6, 2))
        
        color_row = ttk.Frame(tab3); color_row.pack(fill='x', padx=8, pady=2)
        ttk.Button(color_row, text="Bar Color", command=self.choose_bar, width=10).pack(side='left', padx=2)
        self.bar_swatch = tk.Label(color_row, text=" ", bg=self._hex((*self.bar_rgb, 255)), relief="raised", width=3)
        self.bar_swatch.pack(side='left', padx=2)
        ttk.Button(color_row, text="Border", command=self.choose_border, width=10).pack(side='left', padx=2)
        self.border_swatch = tk.Label(color_row, text=" ", bg=self._hex(self.border_color), relief="raised", width=3)
        self.border_swatch.pack(side='left', padx=2)
        ttk.Button(color_row, text="Text Color", command=self.choose_text_color, width=10).pack(side='left', padx=8)
        self.text_swatch = tk.Label(color_row, text=" ", bg=self._hex(self.text_color), relief="raised", width=3)
        self.text_swatch.pack(side='left', padx=2)

        border_frame = ttk.LabelFrame(tab3, text="Metadata Bar Border & Style (independent)", padding=6)
        border_frame.pack(fill='x', padx=8, pady=6)

        bf1 = ttk.Frame(border_frame); bf1.pack(side='left', fill='x', expand=True)
        ttk.Label(bf1, text="Border:").pack(side='left')
        self.border_strength = ttk.Combobox(bf1, values=["Very Thin", "Small", "Medium", "Large"], state="readonly", width=9)
        self.border_strength.current(0)
        self.border_strength.pack(side='left', padx=4)
        self.border_strength.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        bf2 = ttk.Frame(border_frame); bf2.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Label(bf2, text="Style:").pack(side='left')
        self.border_style = ttk.Combobox(bf2, values=["None", "Solid", "Square", "Double", "Dashed", "Glow"], state="readonly", width=11)
        self.border_style.current(1)
        self.border_style.pack(side='left', padx=4)
        self.border_style.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        bf3 = ttk.Frame(border_frame); bf3.pack(side='left', fill='x', expand=True)
        ttk.Label(bf3, text="Radius:").pack(side='left')
        self.corner_radius_choice = ttk.Combobox(bf3, values=list(self.corner_radius_map.keys()), state="readonly", width=8)
        self.corner_radius_choice.current(1)
        self.corner_radius_choice.pack(side='left', padx=4)
        self.corner_radius_choice.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        bf4 = ttk.Frame(border_frame); bf4.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Label(bf4, text="Padding:").pack(side='left')
        self.padding_choice = ttk.Combobox(bf4, values=list(self.padding_map.keys()), state="readonly", width=10)
        self.padding_choice.current(1)
        self.padding_choice.pack(side='left', padx=4)
        self.padding_choice.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Checkbutton(border_frame, text="Bar Shadow", variable=self.bar_shadow, command=self.update_preview).pack(side='left', padx=8)
        ttk.Checkbutton(border_frame, text="Text Outline (CRT)", variable=self.text_shadow, command=self.update_preview).pack(side='left', padx=4)

        # Checkbox means "use gauge instead of default stars"
        ttk.Checkbutton(tab3, text="Use RPG Gauge Ratings (Colors/Health change based on rating. Pretty nifty, eh?)", variable=self.use_stars, command=self.update_preview).pack(anchor='w', padx=8, pady=2)
        # Note: variable is still called use_stars but logic inverted in draw call (True=stars)
        ttk.Checkbutton(tab3, text="Display Rating as Text (e.g. \"92%\")", variable=self.display_rating_as_text, command=self.update_preview).pack(anchor='w', padx=8, pady=2)
        
        # NEW: Star spacing slider
        star_space_frame = ttk.Frame(tab3); star_space_frame.pack(fill='x', padx=8, pady=2)
        ttk.Label(star_space_frame, text="Star Spacing", width=12).pack(side='left')
        self.star_space_scale = ttk.Scale(star_space_frame, from_=0.7, to=1.6, orient="horizontal", variable=self.star_spacing_mult)
        self.star_space_scale.pack(side='left', fill='x', padx=4)
        self.star_space_label = ttk.Label(star_space_frame, text="1.00x", width=6)
        self.star_space_label.pack(side='right')
        self.star_space_scale.config(command=lambda v: self.star_space_label.config(text=f"{float(v):.2f}x"))
        
        # NEW: Vertical mode extra gap between rating and players
        vgap_frame = ttk.Frame(tab3); vgap_frame.pack(fill='x', padx=8, pady=2)
        ttk.Label(vgap_frame, text="Vertical Rating→Player Gap", width=18).pack(side='left')
        self.vgap_scale = ttk.Scale(vgap_frame, from_=0.8, to=2.0, orient="horizontal", variable=self.vertical_player_gap_mult)
        self.vgap_scale.pack(side='left', fill='x', padx=4)
        self.vgap_label = ttk.Label(vgap_frame, text="1.15x", width=6)
        self.vgap_label.pack(side='right')
        self.vgap_scale.config(command=lambda v: self.vgap_label.config(text=f"{float(v):.2f}x"))

        star_opts = ttk.Frame(tab3); star_opts.pack(fill='x', padx=8, pady=2)
        ttk.Label(star_opts, text="Star Design:").pack(side='left', padx=4)
        self.star_style_combo = ttk.Combobox(star_opts, textvariable=self.star_style, 
                                              values=["Classic Filled", "Outlined (★/☆)"], state="readonly", width=16)
        self.star_style_combo.pack(side='left', padx=4)
        self.star_style_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        ttk.Button(star_opts, text="★ Color", command=self.choose_star_color, width=10).pack(side='left', padx=6)
        self.star_swatch = tk.Label(star_opts, text=" ", bg="#ffd700", relief="raised", width=3, height=1)
        self.star_swatch.pack(side='left', padx=2)
        
        ttk.Checkbutton(tab3, text="Vertical Bar Layout", variable=self.bar_vertical, command=self.update_preview).pack(anchor='w', padx=8, pady=2)
        ttk.Checkbutton(tab3, text="Show Field Labels in Vertical Mode (Year, Genre, Publisher, Developer)", variable=self.vertical_labels, command=self.update_preview).pack(anchor='w', padx=8, pady=2)
        ttk.Checkbutton(tab3, text="Hide Metadata Bar Entirely (disable drawing)", variable=self.hide_metadata, command=self.update_preview).pack(anchor='w', padx=8, pady=2)

        pstyle_frame = ttk.Frame(tab3); pstyle_frame.pack(fill='x', padx=8, pady=3)
        ttk.Label(pstyle_frame, text="Player Icon Style:").pack(side='left', padx=4)
        self.player_icon_combo = ttk.Combobox(pstyle_frame, textvariable=self.player_icon_style, 
                                              values=["Players as Text", "Classic", "X", "Dots", "Circles", "Custom Icon"], state="readonly", width=14)
        self.player_icon_combo.current(1)
        self.player_icon_combo.pack(side='left', padx=4)
        self.player_icon_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        ttk.Button(pstyle_frame, text="Load Custom Icon", command=self.load_custom_player_icon, width=16).pack(side='left', padx=4)
        self.custom_player_icon_label = ttk.Label(pstyle_frame, text="No custom icon", foreground="#a0a0b0", width=18)
        self.custom_player_icon_label.pack(side='left', padx=4)
        ttk.Label(pstyle_frame, text="(Pull up your own image to reflect the number of players like a joystick icon)", foreground="#888", font=("TkDefaultFont", 7)).pack(side='left', padx=6)
        
        bar_pat = ttk.Frame(tab3); bar_pat.pack(fill='x', padx=8, pady=2)
        ttk.Label(bar_pat, text="Bar Pattern:").pack(side='left', padx=4)
        self.bar_pattern_combo = ttk.Combobox(bar_pat, textvariable=self.bar_pattern, 
                                            values=["None", "Gradient", "Horizontal Gradient", "Diagonal", "Checkerboard", "Dots", "Stripes", "Grid", "Noise", "Bricks", "Hex", "Scanlines", "Crosshatch", "Lattice"], state="readonly", width=14)
        self.bar_pattern_combo.pack(side='left', padx=4)
        ttk.Button(bar_pat, text="Secondary Color", command=self.choose_bar_color2, width=13).pack(side='left', padx=6)
        self.bar2_swatch = tk.Label(bar_pat, text=" ", bg=self._hex((*self.bar_color2[:3], 255)), relief="raised", width=3, height=1)
        self.bar2_swatch.pack(side='left', padx=2)
        
        texture_frame = ttk.Frame(tab3)
        texture_frame.pack(pady=4)
        ttk.Button(texture_frame, text="Load Bar Texture", command=self.load_bar_texture).pack(side='left', padx=4)
        ttk.Button(texture_frame, text="Unload", command=self.unload_bar_texture).pack(side='left', padx=4)

        ttk.Label(tab3, text="Transparency", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(6,0))
        trans_row = ttk.Frame(tab3); trans_row.pack(fill='x', padx=8)
        self.bar_alpha_label = ttk.Label(trans_row, text="82%", width=4)
        self.bar_alpha_label.pack(side='right')
        ttk.Scale(trans_row, from_=10, to=100, orient="horizontal", variable=self.bar_alpha_pct, 
                  command=lambda v: self.bar_alpha_label.config(text=f"{int(float(v))}%")).pack(side='left', fill='x', padx=4)

        ttk.Label(tab3, text="Text Scale (affects size in preview & output)", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4,0))
        text_scale_frame = ttk.Frame(tab3); text_scale_frame.pack(fill='x', padx=8)
        self.text_scale_label = ttk.Label(text_scale_frame, text="1.00x", width=6)
        self.text_scale_label.pack(side='right')
        ttk.Scale(text_scale_frame, from_=0.6, to=2.0, orient="horizontal", variable=self.text_scale_var, 
                  command=lambda v: self.text_scale_label.config(text=f"{float(v):.2f}x")).pack(side='left', fill='x', padx=4)

        ttk.Label(tab3, text="Bar Position & Size)", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(8,0))
        
        pos_frame = ttk.Frame(tab3); pos_frame.pack(fill='x', padx=8, pady=2)
        
        sf = ttk.Frame(pos_frame); sf.pack(side='left', fill='x', expand=True, padx=3)
        ttk.Label(sf, text="Width", width=7).pack(side='left')
        self.bar_w_scale = ttk.Scale(sf, from_=200, to=1400, orient="horizontal", variable=self.bar_w)
        self.bar_w_scale.pack(side='left', fill='x', padx=3)
        self.bar_w_spin = ttk.Spinbox(sf, textvariable=self.bar_w, from_=200, to=1400, increment=5, width=7, command=self._live_update_preview)
        self.bar_w_spin.pack(side='right', padx=2)
        self.bar_w_label = ttk.Label(sf, textvariable=self.bar_w, width=5)
        self.bar_w_label.pack(side='right')
        
        sf = ttk.Frame(pos_frame); sf.pack(side='left', fill='x', expand=True, padx=3)
        ttk.Label(sf, text="Height", width=7).pack(side='left')
        self.bar_h_scale = ttk.Scale(sf, from_=20, to=300, orient="horizontal", variable=self.bar_height_var)
        self.bar_h_scale.pack(side='left', fill='x', padx=3)
        self.bar_h_spin = ttk.Spinbox(sf, textvariable=self.bar_height_var, from_=20, to=300, increment=5, width=7, command=self._live_update_preview)
        self.bar_h_spin.pack(side='right', padx=2)
        self.bar_h_label = ttk.Label(sf, textvariable=self.bar_height_var, width=5)
        self.bar_h_label.pack(side='right')
        
        sf = ttk.Frame(pos_frame); sf.pack(side='left', fill='x', expand=True, padx=3)
        ttk.Label(sf, text="X Pos", width=7).pack(side='left')
        self.bar_x_scale = ttk.Scale(sf, from_=-400, to=2000, orient="horizontal", variable=self.bar_x_var)
        self.bar_x_scale.pack(side='left', fill='x', padx=3)
        self.bar_x_spin = ttk.Spinbox(sf, textvariable=self.bar_x_var, from_=-400, to=2000, increment=1, width=7, command=self._live_update_preview)
        self.bar_x_spin.pack(side='right', padx=2)
        self.bar_x_label = ttk.Label(sf, textvariable=self.bar_x_var, width=5)
        self.bar_x_label.pack(side='right')
        
        sf = ttk.Frame(pos_frame); sf.pack(side='left', fill='x', expand=True, padx=3)
        ttk.Label(sf, text="Y Pos", width=7).pack(side='left')
        self.bar_y_scale = ttk.Scale(sf, from_=-100, to=800, orient="horizontal", variable=self.bar_y_var)
        self.bar_y_scale.pack(side='left', fill='x', padx=3)
        self.bar_y_spin = ttk.Spinbox(sf, textvariable=self.bar_y_var, from_=-100, to=800, increment=1, width=7, command=self._live_update_preview)
        self.bar_y_spin.pack(side='right', padx=2)
        self.bar_y_label = ttk.Label(sf, textvariable=self.bar_y_var, width=5)
        self.bar_y_label.pack(side='right')

        for spin, var in [(self.bar_w_spin, self.bar_w), (self.bar_h_spin, self.bar_height_var), (self.bar_x_spin, self.bar_x_var), (self.bar_y_spin, self.bar_y_var)]:
            spin.bind("<Return>", lambda e, v=var: self._update_from_entry(v))
            spin.bind("<FocusOut>", lambda e, v=var: self._update_from_entry(v))
        self.bar_w_scale.config(command=lambda v: self._live_update_preview())
        self.bar_h_scale.config(command=lambda v: self._live_update_preview())
        self.bar_x_scale.config(command=lambda v: self._live_update_preview())
        self.bar_y_scale.config(command=lambda v: self._live_update_preview())

        center_frame = ttk.Frame(tab3); center_frame.pack(pady=6)
        ttk.Button(center_frame, text="🎯 Center Bar (recommended)", command=self.center_bar).pack(side='left', padx=4)
        ttk.Button(center_frame, text="Auto-fit Width", command=self.autofit_bar_width).pack(side='left', padx=4)

        ttk.Button(tab3, text="Select Custom Font", command=self.pick_font).pack(pady=6)

    def _update_from_entry(self, var):
        try:
            val = float(var.get())
            is_720p = self.get_current_res() == "720p"
            W = 1920 if is_720p else 640
            if var == self.bar_x_var:
                val = max(-300, min(val, W + 200))
            elif var == self.bar_y_var:
                val = max(-100, min(val, 800 if is_720p else 500))
            elif var == self.bar_w:
                val = max(200, min(val, W - 40))
            elif var == self.bar_height_var:
                val = max(20, min(val, 400))
            var.set(int(val) if var in [self.bar_x_var, self.bar_y_var, self.bar_w, self.bar_height_var] else val)
        except:
            pass
        self.update_preview()

    def _live_update_preview(self):
        self.update_idletasks()
        self.update_preview()

    def center_bar(self):
        is_720p = self.get_current_res() == "720p"
        W = 1920 if is_720p else 640
        bar_w = self.bar_w.get()
        self.bar_x_var.set( max(10, (W - bar_w) // 2 ) )
        self.bar_y_var.set( max(5, int( (720 if is_720p else 480) * 0.04 )) )
        self.update_preview()

    def autofit_bar_width(self):
        is_720p = self.get_current_res() == "720p"
        W = 1920 if is_720p else 640
        target_w = int(W * 0.65) if is_720p else int(W * 0.78)
        self.bar_w.set(target_w)
        self.center_bar()

    def create_additional_tab(self):
        tab_add = ttk.Frame(self.notebook)
        self.notebook.add(tab_add, text="Additional Image")
        self.enable_additional = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab_add, text="Enable Additional Background Image (PNG with transparency supported)", variable=self.enable_additional, command=self.update_preview).pack(anchor='w', padx=8, pady=6)
        ttk.Button(tab_add, text="Select Additional Image (PNG recommended for transparency)", command=self.load_additional_image).pack(pady=4)
        self.additional_label = ttk.Label(tab_add, text="No image selected", foreground="#a0a0b0", width=50)
        self.additional_label.pack(pady=2, padx=8, anchor='w')
        
        for label, var, fromv, tov in [
            ("Scale", self.additional_scale, 0.1, 3.0),
            ("X Position", self.additional_x, 0, 2000),
            ("Y Position", self.additional_y, 0, 1200),
        ]:
            f = ttk.Frame(tab_add); f.pack(fill='x', padx=8, pady=2)
            ttk.Label(f, text=label, width=12).pack(side='left')
            scale = ttk.Scale(f, from_=fromv, to=tov, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            spin = ttk.Spinbox(f, textvariable=var, from_=fromv, to=tov, increment=1 if "Scale" not in label else 0.05, width=7, command=self.update_preview)
            spin.pack(side='right', padx=2)
            lbl = ttk.Label(f, text=f"{var.get():.1f}" if "Scale" in label else str(int(var.get())), width=6)
            lbl.pack(side='right')
            def make_cmd(v=var, l=lbl, lbl_text=label):
                def cmd(val):
                    try:
                        if "Scale" in lbl_text:
                            l.config(text=f"{float(val):.2f}")
                        else:
                            l.config(text=str(int(float(val))))
                    except: pass
                    self.update_preview()
                return cmd
            scale.config(command=make_cmd())
            spin.bind("<Return>", lambda e, v=var: self._update_add_from_entry(v))
            spin.bind("<FocusOut>", lambda e, v=var: self._update_add_from_entry(v))

        center_add = ttk.Frame(tab_add); center_add.pack(pady=4)
        ttk.Button(center_add, text="Center Image", command=self.center_additional).pack(side='left', padx=4)
        ttk.Button(center_add, text="Center + Fit", command=self.center_and_fit_additional).pack(side='left', padx=4)

        ttk.Checkbutton(tab_add, text="Drop Shadow", variable=self.additional_shadow).pack(anchor='w', padx=8, pady=4)
        ttk.Label(tab_add, text="Transparency % (0=invisible, 100=opaque)", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8)
        trans_row = ttk.Frame(tab_add); trans_row.pack(fill='x', padx=8)
        self.add_alpha_label = ttk.Label(trans_row, text="100%", width=4)
        self.add_alpha_label.pack(side='right')
        ttk.Scale(trans_row, from_=0, to=100, orient="horizontal", variable=self.additional_alpha, 
                  command=lambda v: self.add_alpha_label.config(text=f"{int(float(v))}%")).pack(side='left', fill='x', padx=4)

        sep = ttk.Separator(tab_add, orient='horizontal')
        sep.pack(fill='x', padx=8, pady=8)
        ttk.Checkbutton(tab_add, text="Enable Second Additional Image (PNG with transparency)", variable=self.enable_additional2, command=self.update_preview).pack(anchor='w', padx=8, pady=4)
        ttk.Button(tab_add, text="Select Second Additional Image", command=self.load_additional2_image).pack(pady=2)
        self.additional2_label = ttk.Label(tab_add, text="No image selected", foreground="#a0a0b0", width=50)
        self.additional2_label.pack(pady=2, padx=8, anchor='w')
        
        for label, var, fromv, tov in [
            ("Scale 2", self.additional2_scale, 0.1, 3.0),
            ("X Pos 2", self.additional2_x, 0, 2000),
            ("Y Pos 2", self.additional2_y, 0, 1200),
        ]:
            f = ttk.Frame(tab_add); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=10).pack(side='left')
            scale = ttk.Scale(f, from_=fromv, to=tov, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            spin = ttk.Spinbox(f, textvariable=var, from_=fromv, to=tov, increment=0.05 if "Scale" in label else 1, width=7, command=self.update_preview)
            spin.pack(side='right', padx=2)
            def make_cmd2(v=var, lbl_text=label):
                def cmd(val):
                    self.update_preview()
                return cmd
            scale.config(command=make_cmd2())
        
        center_add2 = ttk.Frame(tab_add); center_add2.pack(pady=4)
        ttk.Button(center_add2, text="Center Image 2", command=self.center_additional2).pack(side='left', padx=4)
        ttk.Button(center_add2, text="Center + Fit 2", command=self.center_and_fit_additional2).pack(side='left', padx=4)

        ttk.Checkbutton(tab_add, text="Drop Shadow (Image 2)", variable=self.additional2_shadow).pack(anchor='w', padx=8, pady=2)
        ttk.Label(tab_add, text="Transparency % (Image 2)", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8)
        trans_row2 = ttk.Frame(tab_add); trans_row2.pack(fill='x', padx=8, pady=2)
        self.add2_alpha_label = ttk.Label(trans_row2, text="80%", width=4)
        self.add2_alpha_label.pack(side='right')
        ttk.Scale(trans_row2, from_=0, to=100, orient="horizontal", variable=self.additional2_alpha, 
                  command=lambda v: self.add2_alpha_label.config(text=f"{int(float(v))}%")).pack(side='left', fill='x', padx=4)

    def _update_add_from_entry(self, var):
        try:
            val = float(var.get())
            is_720p = self.get_current_res() == "720p"
            max_x = 1400 if is_720p else 800
            max_y = 800 if is_720p else 550
            if var == self.additional_x:
                val = max(0, min(val, max_x))
            elif var == self.additional_y:
                val = max(0, min(val, max_y))
            elif var == self.additional_scale:
                val = max(0.1, min(val, 4.0))
            var.set(round(val, 2) if var == self.additional_scale else int(val))
        except:
            pass
        self.update_preview()

    def center_additional(self):
        is_720p = self.get_current_res() == "720p"
        W = 1280 if is_720p else 640
        H = 720 if is_720p else 480
        self.additional_x.set( int(W * 0.35) )
        self.additional_y.set( int(H * 0.25) )
        self.update_preview()

    def center_and_fit_additional(self):
        is_720p = self.get_current_res() == "720p"
        W = 1280 if is_720p else 640
        H = 720 if is_720p else 480
        if self.additional_image and os.path.exists(self.additional_image):
            try:
                with Image.open(self.additional_image) as im:
                    iw, ih = im.size
                target_w = int(W * 0.45)
                sc = target_w / iw
                self.additional_scale.set(round(sc, 2))
                self.additional_x.set( int((W - target_w) / 2) )
                self.additional_y.set( int(H * 0.18) )
            except:
                self.center_additional()
        else:
            self.center_additional()
        self.update_preview()

    def center_additional2(self):
        is_720p = self.get_current_res() == "720p"
        W = 1280 if is_720p else 640
        H = 720 if is_720p else 480
        self.additional2_x.set(int(W * 0.4))
        self.additional2_y.set(int(H * 0.3))
        self.update_preview()

    def center_and_fit_additional2(self):
        is_720p = self.get_current_res() == "720p"
        W = 1280 if is_720p else 640
        H = 720 if is_720p else 480
        if self.additional2_image and os.path.exists(self.additional2_image):
            try:
                with Image.open(self.additional2_image) as im:
                    iw, ih = im.size
                target_w = int(W * 0.35)
                sc = target_w / iw
                self.additional2_scale.set(round(sc, 2))
                self.additional2_x.set(int((W - target_w) / 2))
                self.additional2_y.set(int(H * 0.22))
            except:
                self.center_additional2()
        else:
            self.center_additional2()
        self.update_preview()

    def create_description_tab(self):
        tab_desc = ttk.Frame(self.notebook)
        self.notebook.add(tab_desc, text="Description")
        ttk.Checkbutton(tab_desc, text="Enable Description Box", variable=self.use_description, command=self.update_preview).pack(anchor='w', padx=8, pady=6)
        
        color_row = ttk.Frame(tab_desc); color_row.pack(fill='x', padx=8, pady=4)
        ttk.Button(color_row, text="Box Color", command=self.choose_desc, width=11).pack(side='left', padx=2)
        self.desc_swatch = tk.Label(color_row, text=" ", bg=self._hex((*self.desc_rgb, 255)), relief="raised", width=3)
        self.desc_swatch.pack(side='left', padx=2)
        ttk.Button(color_row, text="Border", command=self.choose_desc_border, width=8).pack(side='left', padx=2)
        self.desc_border_swatch = tk.Label(color_row, text=" ", bg=self._hex(self.desc_border_color), relief="raised", width=3)
        self.desc_border_swatch.pack(side='left', padx=2)
        ttk.Button(color_row, text="Text Color", command=self.choose_desc_text_color, width=10).pack(side='left', padx=2)
        self.desc_text_swatch = tk.Label(color_row, text=" ", bg=self._hex(self.desc_text_color), relief="raised", width=3)
        self.desc_text_swatch.pack(side='left', padx=2)
        ttk.Checkbutton(color_row, text="Shadow", variable=self.desc_shadow).pack(side='left', padx=8)
        ttk.Button(color_row, text="Custom Font", command=self.pick_desc_font, width=12).pack(side='left', padx=2)
        
        gframe = ttk.Frame(tab_desc); gframe.pack(fill='x', padx=8, pady=4)
        ttk.Label(gframe, text="Pattern:").pack(side='left', padx=4)
        self.desc_pattern_combo = ttk.Combobox(gframe, textvariable=self.desc_pattern, 
                                             values=["None", "Gradient", "Horizontal Gradient", "Diagonal", "Checkerboard", "Dots", "Stripes", "Grid", "Noise", "Bricks", "Hex", "Scanlines", "Crosshatch", "Lattice"], state="readonly", width=14)
        self.desc_pattern_combo.pack(side='left', padx=4)
        ttk.Button(gframe, text="Secondary Color", command=self.choose_desc_color2, width=13).pack(side='left', padx=6)
        self.desc2_swatch = tk.Label(gframe, text=" ", bg=self._hex((*self.desc_color2[:3], 255)), relief="raised", width=3, height=1)
        self.desc2_swatch.pack(side='left', padx=2)
        ttk.Button(gframe, text="Load Texture", command=self.load_desc_texture).pack(side='left', padx=8)
        ttk.Button(gframe, text="Copy from Metadata Bar", command=self.copy_metadata_to_desc).pack(side='left', padx=8)

        border_frame = ttk.LabelFrame(tab_desc, text="Description Border", padding=6)
        border_frame.pack(fill='x', padx=8, pady=6)

        bf1 = ttk.Frame(border_frame); bf1.pack(side='left', fill='x', expand=True)
        ttk.Label(bf1, text="Border:").pack(side='left')
        self.desc_border_strength_combo = ttk.Combobox(bf1, textvariable=self.desc_border_strength, values=["Very Thin", "Small", "Medium", "Large"], state="readonly", width=9)
        self.desc_border_strength_combo.pack(side='left', padx=4)
        self.desc_border_strength_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        bf2 = ttk.Frame(border_frame); bf2.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Label(bf2, text="Style:").pack(side='left')
        self.desc_border_style_combo = ttk.Combobox(bf2, textvariable=self.desc_border_style, 
            values=["None", "Solid", "Square", "Double", "Dashed", "Glow"], state="readonly", width=11)
        self.desc_border_style_combo.pack(side='left', padx=4)
        self.desc_border_style_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        bf3 = ttk.Frame(border_frame); bf3.pack(side='left', fill='x', expand=True)
        ttk.Label(bf3, text="Radius:").pack(side='left')
        self.desc_corner_radius_combo = ttk.Combobox(bf3, textvariable=self.desc_corner_radius_choice, values=list(self.corner_radius_map.keys()), state="readonly", width=8)
        self.desc_corner_radius_combo.pack(side='left', padx=4)
        self.desc_corner_radius_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Checkbutton(border_frame, text="Text Outline (CRT)", variable=self.desc_text_outline, command=self.update_preview).pack(side='left', padx=8)

        ttk.Label(tab_desc, text="Size & Position", style="Section.TLabel").pack(anchor='w', padx=8, pady=(8,2))
        
        for label, var, fromv, tov in [
            ("Width", self.desc_w, 80, 900),
            ("Height", self.desc_h, 60, 600),
            ("X Pos", self.desc_x, -300, 1400),
            ("Y Pos", self.desc_y, -100, 1000),
        ]:
            f = ttk.Frame(tab_desc); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=8).pack(side='left')
            scale = ttk.Scale(f, from_=fromv, to=tov, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            spin = ttk.Spinbox(f, textvariable=var, from_=fromv, to=tov, increment=1, width=7, command=self.update_preview)
            spin.pack(side='right', padx=2)
            lbl = ttk.Label(f, text=str(int(var.get())), width=5)
            lbl.pack(side='right')
            def make_upd(l=lbl, v=var):
                def upd(val):
                    try: l.config(text=str(int(float(val))))
                    except: pass
                    self.update_preview()
                return upd
            scale.config(command=make_upd())
            spin.bind("<Return>", lambda e, v=var: self._update_desc_entry(v))
            spin.bind("<FocusOut>", lambda e, v=var: self._update_desc_entry(v))

        ttk.Label(tab_desc, text="Text Scale (fixes previous broken scaling)", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(6,0))
        desc_text_frame = ttk.Frame(tab_desc); desc_text_frame.pack(fill='x', padx=8)
        self.desc_font_label = ttk.Label(desc_text_frame, text="1.00x", width=6)
        self.desc_font_label.pack(side='right')
        ttk.Scale(desc_text_frame, from_=0.5, to=2.0, orient="horizontal", variable=self.desc_font_scale, 
                  command=lambda v: self.desc_font_label.config(text=f"{float(v):.2f}x")).pack(side='left', fill='x', padx=4)

        ttk.Label(tab_desc, text="Box Transparency % (affects fill alpha)", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(6,0))
        desc_trans_frame = ttk.Frame(tab_desc); desc_trans_frame.pack(fill='x', padx=8)
        self.desc_alpha_label = ttk.Label(desc_trans_frame, text="85%", width=4)
        self.desc_alpha_label.pack(side='right')
        ttk.Scale(desc_trans_frame, from_=10, to=100, orient="horizontal", variable=self.desc_alpha_pct, 
                  command=lambda v: self.desc_alpha_label.config(text=f"{int(float(v))}%")).pack(side='left', fill='x', padx=4)

    def _update_desc_entry(self, var):
        try:
            val = float(var.get())
            is_720p = self.get_current_res() == "720p"
            maxv = 1400 if is_720p else 500
            if var in [self.desc_x, self.desc_y]:
                val = max(-300, min(val, maxv + 200))
            elif var == self.desc_w:
                val = max(60, min(val, 1100 if is_720p else 450))
            elif var == self.desc_h:
                val = max(40, min(val, 700 if is_720p else 350))
            var.set(int(val))
        except:
            pass
        self.update_preview()

    def create_media_tab(self):
        tab4 = ttk.Frame(self.notebook)
        self.notebook.add(tab4, text="Physical Media")
        ttk.Label(tab4, text="Physical Media Overlay (box art / disc)", style="Section.TLabel").pack(anchor='w', padx=8, pady=6)
        ttk.Label(tab4, text="Size Preset", font=("TkDefaultFont", 9)).pack(anchor='w', padx=8)
        self.media_size = ttk.Combobox(tab4, values=["Small", "Medium", "Large"], state="readonly", width=25)
        self.media_size.current(1)
        self.media_size.pack(padx=8, pady=2, anchor='w')

        custom_size_frame = ttk.Frame(tab4); custom_size_frame.pack(fill='x', padx=8, pady=2)
        ttk.Label(custom_size_frame, text="Custom Size", width=12).pack(side='left')
        self.media_custom_scale = ttk.Scale(custom_size_frame, from_=50, to=400, orient="horizontal", variable=self.media_custom_size)
        self.media_custom_scale.pack(side='left', fill='x', padx=4)
        self.media_custom_spin = ttk.Spinbox(custom_size_frame, textvariable=self.media_custom_size, from_=50, to=400, increment=5, width=7, command=self.update_preview)
        self.media_custom_spin.pack(side='right', padx=2)
        self.media_custom_label = ttk.Label(custom_size_frame, textvariable=self.media_custom_size, width=5)
        self.media_custom_label.pack(side='right')
        def media_custom_cmd(val):
            self.update_preview()
        self.media_custom_scale.config(command=media_custom_cmd)
        self.media_custom_spin.bind("<Return>", lambda e: self.update_preview())
        self.media_custom_spin.bind("<FocusOut>", lambda e: self.update_preview())

        ttk.Label(tab4, text="Position Offset from Bottom-Right", font=("TkDefaultFont", 9)).pack(anchor='w', padx=8, pady=(8,2))
        for label, var, from_, to_ in [("Right Offset X", self.media_x, -1000, 2000), ("Bottom Offset Y", self.media_y, -1000, 2000)]:
            f = ttk.Frame(tab4); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=16).pack(side='left')
            scale = ttk.Scale(f, from_=from_, to=to_, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            spin = ttk.Spinbox(f, textvariable=var, from_=from_, to=to_, increment=1, width=7, command=self.update_preview)
            spin.pack(side='right', padx=2)
            lbl = ttk.Label(f, text=str(int(var.get())), width=5)
            lbl.pack(side='right')
            def make_cmd(l=lbl, v=var):
                def cmd(val):
                    try: l.config(text=str(int(float(val))))
                    except: pass
                    self.update_preview()
                return cmd
            scale.config(command=make_cmd())
            spin.bind("<Return>", lambda e, v=var: self._update_media_entry(v))
            spin.bind("<FocusOut>", lambda e, v=var: self._update_media_entry(v))

        ttk.Checkbutton(tab4, text="Drop Shadow", variable=self.media_shadow).pack(anchor='w', padx=8, pady=6)

        ttk.Label(tab4, text="Transparency %", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4,0))
        trans_row = ttk.Frame(tab4); trans_row.pack(fill='x', padx=8)
        self.media_alpha_label = ttk.Label(trans_row, text="100%", width=4)
        self.media_alpha_label.pack(side='right')
        ttk.Scale(trans_row, from_=10, to=100, orient="horizontal", variable=self.media_alpha,
                  command=lambda v: self.media_alpha_label.config(text=f"{int(float(v))}%")).pack(side='left', fill='x', padx=4)

    def create_optional_media_tab(self):
        tab_opt = ttk.Frame(self.notebook)
        self.notebook.add(tab_opt, text="Optional Media")
        ttk.Label(tab_opt, text="Optional Media Overlay (from Optional Media Folder", style="Section.TLabel").pack(anchor='w', padx=8, pady=6)
        
        note = ttk.Label(tab_opt, text="Note: Select & enable 'Optional Media Folder' in Paths tab to use per-game images here. This is separate from Physical Media. Overlay is disabled by default until you enable the folder.", font=("TkDefaultFont", 8), foreground="#888")
        note.pack(anchor='w', padx=8, pady=2)
        
        ttk.Checkbutton(tab_opt, text="Enable Optional Media Overlay", variable=self.enable_optional_media, command=self.update_preview).pack(anchor='w', padx=8, pady=4)
        
        ttk.Label(tab_opt, text="Size Preset", font=("TkDefaultFont", 9)).pack(anchor='w', padx=8)
        self.opt_media_size = ttk.Combobox(tab_opt, values=["Small", "Medium", "Large"], state="readonly", width=25)
        self.opt_media_size.current(1)
        self.opt_media_size.pack(padx=8, pady=2, anchor='w')
        self.opt_media_size.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        custom_size_frame_opt = ttk.Frame(tab_opt); custom_size_frame_opt.pack(fill='x', padx=8, pady=2)
        ttk.Label(custom_size_frame_opt, text="Custom Size", width=12).pack(side='left')
        self.opt_media_custom_scale = ttk.Scale(custom_size_frame_opt, from_=50, to=400, orient="horizontal", variable=self.opt_media_custom_size)
        self.opt_media_custom_scale.pack(side='left', fill='x', padx=4)
        self.opt_media_custom_spin = ttk.Spinbox(custom_size_frame_opt, textvariable=self.opt_media_custom_size, from_=50, to=400, increment=5, width=7, command=self.update_preview)
        self.opt_media_custom_spin.pack(side='right', padx=2)
        self.opt_media_custom_label = ttk.Label(custom_size_frame_opt, textvariable=self.opt_media_custom_size, width=5)
        self.opt_media_custom_label.pack(side='right')
        def opt_custom_cmd(val):
            self.update_preview()
        self.opt_media_custom_scale.config(command=opt_custom_cmd)
        self.opt_media_custom_spin.bind("<Return>", lambda e: self.update_preview())
        self.opt_media_custom_spin.bind("<FocusOut>", lambda e: self.update_preview())

        ttk.Label(tab_opt, text="Position Offset from Bottom-Right", font=("TkDefaultFont", 9)).pack(anchor='w', padx=8, pady=(8,2))
        for label, var, from_, to_ in [("Right Offset X", self.opt_media_x, -1000, 2000), ("Bottom Offset Y", self.opt_media_y, -1000, 2000)]:
            f = ttk.Frame(tab_opt); f.pack(fill='x', padx=8, pady=1)
            ttk.Label(f, text=label, width=16).pack(side='left')
            scale = ttk.Scale(f, from_=from_, to=to_, orient="horizontal", variable=var)
            scale.pack(side='left', fill='x', padx=4)
            spin = ttk.Spinbox(f, textvariable=var, from_=from_, to=to_, increment=1, width=7, command=self.update_preview)
            spin.pack(side='right', padx=2)
            lbl = ttk.Label(f, text=str(int(var.get())), width=5)
            lbl.pack(side='right')
            def make_cmd(l=lbl, v=var):
                def cmd(val):
                    try: l.config(text=str(int(float(val))))
                    except: pass
                    self.update_preview()
                return cmd
            scale.config(command=make_cmd())
            spin.bind("<Return>", lambda e, v=var: self._update_opt_entry(v))
            spin.bind("<FocusOut>", lambda e, v=var: self._update_opt_entry(v))

        ttk.Checkbutton(tab_opt, text="Drop Shadow", variable=self.opt_media_shadow).pack(anchor='w', padx=8, pady=6)

        ttk.Label(tab_opt, text="Transparency %", font=("TkDefaultFont", 8)).pack(anchor='w', padx=8, pady=(4,0))
        trans_row = ttk.Frame(tab_opt); trans_row.pack(fill='x', padx=8)
        self.opt_media_alpha_label = ttk.Label(trans_row, text="90%", width=4)
        self.opt_media_alpha_label.pack(side='right')
        ttk.Scale(trans_row, from_=10, to=100, orient="horizontal", variable=self.opt_media_alpha,
                  command=lambda v: self.opt_media_alpha_label.config(text=f"{int(float(v))}%")).pack(side='left', fill='x', padx=4)

    def _update_opt_entry(self, var):
        try:
            val = float(var.get())
            var.set(int(val))
        except:
            pass
        self.update_preview()

    def _update_media_entry(self, var):
        try:
            val = float(var.get())
            var.set(int(val))
        except:
            pass
        self.update_preview()

    def create_preview_tab(self):
        tab5 = ttk.Frame(self.notebook)
        self.notebook.add(tab5, text="Preview")
        ttk.Label(tab5, text="Live Preview - Accurately reflects final position/size for CRT or 720p mode. Click elements to drag & reposition.", style="Section.TLabel").pack(anchor='w', padx=8, pady=6)
        
        self.preview_canvas = tk.Canvas(tab5, width=560, height=315, bg="#111111", highlightthickness=2, highlightbackground="#5b8cff")
        self.preview_canvas.pack(padx=6, pady=4, side='left')

        self.preview_canvas.bind("<Button-1>", self._on_preview_click)
        self.preview_canvas.bind("<B1-Motion>", self._on_preview_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_preview_release)
        self._drag_element = None
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._preview_scale = 1.0
        self._preview_target_size = (640, 480)
        
        info_frame = ttk.Frame(tab5); info_frame.pack(fill='x', padx=10)
        self.preview_info = ttk.Label(info_frame, text="Preview scales to fit. Drag elements to reposition. Layer order editable below.", font=("TkDefaultFont", 8), foreground="#aaa")
        self.preview_info.pack(side='left')
        
        btn_frame = ttk.Frame(tab5); btn_frame.pack(pady=6)
        ttk.Button(btn_frame, text="🔄 Refresh Preview", command=self.update_preview).pack(side='left', padx=4)
        ttk.Button(btn_frame, text="Center All", command=self.center_all_elements).pack(side='left', padx=4)

        layer_frame = ttk.LabelFrame(tab5, text="Layer Order (last = on top)", padding=6)
        layer_frame.pack(fill='x', padx=10, pady=8)

        self.layer_listbox = tk.Listbox(layer_frame, height=4, width=22, exportselection=False)
        self.layer_listbox.pack(side='left', padx=4)
        self._refresh_layer_listbox()

        btns = ttk.Frame(layer_frame)
        btns.pack(side='left', padx=6)
        ttk.Button(btns, text="↑ Move Up", width=12, command=self.move_layer_up).pack(pady=2)
        ttk.Button(btns, text="↓ Move Down", width=12, command=self.move_layer_down).pack(pady=2)
        ttk.Label(btns, text="Drag or use arrows\nto change stacking", font=("TkDefaultFont", 7), foreground="#888").pack(pady=4)

        self.layer_listbox.bind("<<ListboxSelect>>", lambda e: self.update_preview())

    def center_all_elements(self):
        self.center_bar()
        self.center_additional()
        is_720p = self.get_current_res() == "720p"
        W = 1280 if is_720p else 640
        self.desc_x.set( max(20, (W - self.desc_w.get()) // 2 ) )
        self.update_preview()

    def _refresh_layer_listbox(self):
        if not hasattr(self, 'layer_listbox'):
            return
        self.layer_listbox.delete(0, tk.END)
        display_names = {
            "additional": "Additional Image (top)",
            "additional2": "Additional Image 2",
            "media": "Physical Media",
            "metadata": "Metadata Bar",
            "description": "Description Box",
            "optional_media": "Optional Media"
        }
        for key in self.layer_order:
            self.layer_listbox.insert(tk.END, display_names.get(key, key))

    def move_layer_up(self):
        sel = self.layer_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        self.layer_order[idx-1], self.layer_order[idx] = self.layer_order[idx], self.layer_order[idx-1]
        self._refresh_layer_listbox()
        self.layer_listbox.selection_set(idx-1)
        self.update_preview()

    def move_layer_down(self):
        sel = self.layer_listbox.curselection()
        if not sel or sel[0] == len(self.layer_order) - 1:
            return
        idx = sel[0]
        self.layer_order[idx+1], self.layer_order[idx] = self.layer_order[idx], self.layer_order[idx+1]
        self._refresh_layer_listbox()
        self.layer_listbox.selection_set(idx+1)
        self.update_preview()

    def _on_preview_click(self, event):
        if not hasattr(self, '_preview_scale'):
            return
        scale = self._preview_scale
        target_w, target_h = self._preview_target_size

        canvas_x = event.x
        canvas_y = event.y
        target_x = int(canvas_x / scale)
        target_y = int(canvas_y / scale)

        self._drag_element = None
        self._drag_offset_x = 0
        self._drag_offset_y = 0

        is_720p = self.get_current_res() == "720p"

        bar_w = int(self.bar_w.get())
        bar_x = int(self.bar_x_var.get())
        bar_y = int(self.bar_y_var.get())
        
        # IMPROVED: Tighter hitbox for vertical mode (was too easy to grab)
        if self.bar_vertical.get():
            bar_h = 220  # taller but we use tighter tol
            tol = 5      # reduced tolerance
        else:
            bar_h = 70
            tol = 8
        
        if (bar_x - tol) <= target_x <= (bar_x + bar_w + tol) and (bar_y - tol) <= target_y <= (bar_y + bar_h + tol):
            self._drag_element = "metadata"
            self._drag_offset_x = target_x - bar_x
            self._drag_offset_y = target_y - bar_y
            return

        if self.use_description.get():
            desc_x = int(self.desc_x.get())
            desc_y = int(self.desc_y.get())
            desc_w = int(self.desc_w.get())
            desc_h = int(self.desc_h.get())
            if desc_x <= target_x <= desc_x + desc_w and desc_y <= target_y <= desc_y + desc_h:
                self._drag_element = "description"
                self._drag_offset_x = target_x - desc_x
                self._drag_offset_y = target_y - desc_y
                return

        if self.enable_additional.get() and self.additional_image:
            ax = int(self.additional_x.get())
            ay = int(self.additional_y.get())
            try:
                with Image.open(self.additional_image) as im:
                    aw = int(im.width * self.additional_scale.get())
                    ah = int(im.height * self.additional_scale.get())
            except:
                aw, ah = 200, 150
            if ax <= target_x <= ax + aw and ay <= target_y <= ay + ah:
                self._drag_element = "additional"
                self._drag_offset_x = target_x - ax
                self._drag_offset_y = target_y - ay
                return

        if self.enable_additional2.get() and self.additional2_image:
            ax = int(self.additional2_x.get())
            ay = int(self.additional2_y.get())
            try:
                with Image.open(self.additional2_image) as im:
                    aw = int(im.width * self.additional2_scale.get())
                    ah = int(im.height * self.additional2_scale.get())
            except:
                aw, ah = 180, 120
            if ax <= target_x <= ax + aw and ay <= target_y <= ay + ah:
                self._drag_element = "additional2"
                self._drag_offset_x = target_x - ax
                self._drag_offset_y = target_y - ay
                return

        msize = int(self.media_custom_size.get() * (1.8 if is_720p else 1.0))
        mx = target_w - msize - int(self.media_x.get())
        my = target_h - msize - int(self.media_y.get())
        tol = 30
        if (mx - tol) <= target_x <= (mx + msize + tol) and (my - tol) <= target_y <= (my + msize + tol):
            self._drag_element = "media"
            self._drag_offset_x = target_x - mx
            self._drag_offset_y = target_y - my

        if self.enable_optional_media.get():
            osize = int(self.opt_media_custom_size.get() * (1.8 if is_720p else 1.0))
            ox = target_w - osize - int(self.opt_media_x.get())
            oy = target_h - osize - int(self.opt_media_y.get())
            if (ox - tol) <= target_x <= (ox + osize + tol) and (oy - tol) <= target_y <= (oy + osize + tol):
                self._drag_element = "optional_media"
                self._drag_offset_x = target_x - ox
                self._drag_offset_y = target_y - oy

    def _on_preview_drag(self, event):
        if not self._drag_element or not hasattr(self, '_preview_scale'):
            return
        scale = self._preview_scale
        target_w, target_h = self._preview_target_size

        target_x = int(event.x / scale)
        target_y = int(event.y / scale)

        new_x = target_x - self._drag_offset_x
        new_y = target_y - self._drag_offset_y

        if self._drag_element == "metadata":
            self.bar_x_var.set(max(-300, min(new_x, target_w + 100)))
            self.bar_y_var.set(max(-100, min(new_y, target_h + 50)))
        elif self._drag_element == "description":
            self.desc_x.set(max(-300, min(new_x, target_w + 100)))
            self.desc_y.set(max(-100, min(new_y, target_h + 50)))
        elif self._drag_element == "additional":
            self.additional_x.set(max(-300, min(new_x, target_w + 100)))
            self.additional_y.set(max(-100, min(new_y, target_h + 50)))
        elif self._drag_element == "additional2":
            self.additional2_x.set(max(-300, min(new_x, target_w + 100)))
            self.additional2_y.set(max(-100, min(new_y, target_h + 50)))
        elif self._drag_element == "media":
            msize = int(self.media_custom_size.get() * (1.8 if target_w > 700 else 1.0))
            new_mx = target_w - msize - new_x
            new_my = target_h - msize - new_y
            self.media_x.set(new_mx)
            self.media_y.set(new_my)
        elif self._drag_element == "optional_media":
            osize = int(self.opt_media_custom_size.get() * (1.8 if target_w > 700 else 1.0))
            new_ox = target_w - osize - new_x
            new_oy = target_h - osize - new_y
            self.opt_media_x.set(new_ox)
            self.opt_media_y.set(new_oy)

        self.update_preview()

    def _on_preview_release(self, event):
        self._drag_element = None
        self.update_preview()

    def _draw_additional_in_preview(self, preview_img, target_W, target_H, is_720p):
        if not (self.enable_additional.get() and self.additional_image):
            return
        try:
            add_img = Image.open(self.additional_image).convert("RGBA")
            add_w = int(add_img.width * self.additional_scale.get())
            add_h = int(add_img.height * self.additional_scale.get())
            add_img = add_img.resize((add_w, add_h), Image.LANCZOS)
            ax = int(self.additional_x.get())
            ay = int(self.additional_y.get())
            alpha = self.additional_alpha.get()
            
            if self.additional_shadow.get():
                shadow = Image.new("RGBA", (add_w + 10, add_h + 10), (0,0,0,0))
                sd = ImageDraw.Draw(shadow)
                sd.rounded_rectangle([4,4, add_w+4, add_h+4], radius=6, fill=(0,0,0, int(110 * alpha / 100)))
                shadow = shadow.filter(ImageFilter.GaussianBlur(4))
                preview_img.alpha_composite(shadow, (ax, ay))
            
            if alpha < 100:
                r, g, b, a = add_img.split()
                a = a.point(lambda p: int(p * alpha / 100))
                add_img = Image.merge("RGBA", (r, g, b, a))
            preview_img.alpha_composite(add_img, (ax, ay))
        except Exception as e:
            print("Additional preview error:", e)

    def _draw_additional2_in_preview(self, preview_img, target_W, target_H, is_720p):
        if not (self.enable_additional2.get() and self.additional2_image):
            return
        try:
            add_img = Image.open(self.additional2_image).convert("RGBA")
            add_w = int(add_img.width * self.additional2_scale.get())
            add_h = int(add_img.height * self.additional2_scale.get())
            add_img = add_img.resize((add_w, add_h), Image.LANCZOS)
            ax = int(self.additional2_x.get())
            ay = int(self.additional2_y.get())
            alpha = self.additional2_alpha.get()
            
            if self.additional2_shadow.get():
                shadow = Image.new("RGBA", (add_w + 10, add_h + 10), (0,0,0,0))
                sd = ImageDraw.Draw(shadow)
                sd.rounded_rectangle([4,4, add_w+4, add_h+4], radius=6, fill=(0,0,0, int(110 * alpha / 100)))
                shadow = shadow.filter(ImageFilter.GaussianBlur(4))
                preview_img.alpha_composite(shadow, (ax, ay))
            
            if alpha < 100:
                r, g, b, a = add_img.split()
                a = a.point(lambda p: int(p * alpha / 100))
                add_img = Image.merge("RGBA", (r, g, b, a))
            preview_img.alpha_composite(add_img, (ax, ay))
        except Exception as e:
            print("Additional2 preview error:", e)

    def _draw_media_placeholder_in_preview(self, preview_img, target_W, target_H, is_720p):
        try:
            media_size = int(self.media_custom_size.get() * (1.8 if is_720p else 1.0))
            mx = target_W - media_size - int(self.media_x.get())
            my = target_H - media_size - int(self.media_y.get())
            
            d = ImageDraw.Draw(preview_img)
            overlay = Image.new("RGBA", preview_img.size, (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            od.rounded_rectangle([mx, my, mx+media_size, my+media_size], radius=8, fill=(20,20,30,160), outline=(255,255,255,200), width=2)
            preview_img.alpha_composite(overlay)
            
            try:
                label_font = ImageFont.truetype(resource_path("DejaVuSans-Bold.ttf"), max(10, int(11 * (1.5 if is_720p else 1))))
            except:
                label_font = ImageFont.load_default()
            d.text((mx + 8, my + 8), "PHYSICAL MEDIA", fill=(200,200,220,220), font=label_font)
        except Exception as e:
            print("Media preview placeholder error:", e)

    def _draw_optional_media_in_preview(self, preview_img, target_W, target_H, is_720p):
        if not self.enable_optional_media.get():
            return
        try:
            media_size = int(self.opt_media_custom_size.get() * (1.8 if is_720p else 1.0))
            mx = target_W - media_size - int(self.opt_media_x.get())
            my = target_H - media_size - int(self.opt_media_y.get())
            
            d = ImageDraw.Draw(preview_img)
            overlay = Image.new("RGBA", preview_img.size, (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            od.rounded_rectangle([mx, my, mx+media_size, my+media_size], radius=8, fill=(30,20,40,140), outline=(180,255,180,220), width=2)
            preview_img.alpha_composite(overlay)
            
            try:
                label_font = ImageFont.truetype(resource_path("DejaVuSans-Bold.ttf"), max(10, int(11 * (1.5 if is_720p else 1))))
            except:
                label_font = ImageFont.load_default()
            d.text((mx + 8, my + 8), "OPTIONAL MEDIA", fill=(200,255,200,220), font=label_font)
        except Exception as e:
            print("Optional media preview placeholder error:", e)

    def _draw_metadata_in_preview(self, preview_img, target_W, target_H):
        if self.hide_metadata.get():
            return
        bar_w = int(self.bar_w.get())
        bar_x = int(self.bar_x_var.get())
        bar_y = int(self.bar_y_var.get())
        
        bar_x = max(-300, min(bar_x, target_W + 100))
        bar_y = max(-100, min(bar_y, target_H + 50))
        
        dummy_meta = {"year": "1994", "genre": "Platformer", "publisher": "Duckdog Entertainment", "developer": "Horse Masters", "rating": "0.92", "players": "1-4", "raw_name": "Preview Game"}
        
        text_sc = self.text_scale_var.get()
        draw_metadata_bar(
            preview_img, bar_x, bar_y, bar_w, dummy_meta, 
            (*self.bar_rgb, int(255 * self.bar_alpha_pct.get() / 100)), 
            self.border_color, 
            self.border_width_map.get(self.border_strength.get(), 2), 
            self.border_style.get(), 
            int(self.corner_radius_map.get(self.corner_radius_choice.get(), 10)), 
            self.bar_shadow.get(), 
            self.padding_map.get(self.padding_choice.get(), 1.0),
            ImageFont.load_default(), 
            not self.use_stars.get(),   # not checkbox -> stars by default
            text_sc,
            vertical=self.bar_vertical.get(), 
            use_player_text=(self.player_icon_style.get() == "Players as Text"),
            text_color=self.text_color,
            custom_font_path=self.custom_font,
            vertical_labels=self.vertical_labels.get(),
            gradient=(self.bar_pattern.get() == "Gradient"),
            color2=self.bar_color2,
            player_icon_style=self.player_icon_style.get(),
            bar_height=self.bar_height_var.get(),
            custom_player_icon_path=self.custom_player_icon,
            display_rating_as_text=self.display_rating_as_text.get(),
            star_style=self.star_style.get(),
            star_color=self.star_color,
            star_spacing_mult=self.star_spacing_mult.get(),
            vertical_player_gap_mult=self.vertical_player_gap_mult.get()
        )

    def _draw_description_in_preview(self, preview_img, target_W, target_H):
        if not self.use_description.get():
            return
        desc_x = int(self.desc_x.get())
        desc_y = int(self.desc_y.get())
        desc_w = int(self.desc_w.get())
        desc_h = int(self.desc_h.get())
        desc_text_sc = self.desc_font_scale.get()
        try:
            if self.desc_custom_font and os.path.exists(self.desc_custom_font):
                fpath = self.desc_custom_font
            else:
                fpath = resource_path("DejaVuSans-Bold.ttf")
            desc_font_size = max(8, int(12 * desc_text_sc))
            desc_font = ImageFont.truetype(fpath, desc_font_size)
        except Exception:
            desc_font = ImageFont.load_default()
        alpha = int(255 * self.desc_alpha_pct.get() / 100)
        draw_description_box(
            preview_img, desc_x, desc_y, desc_w, desc_h, 
            "This is a sample description box. The text scaling and positioning display correctly in both CRT and 720p modes.",
            (*self.desc_rgb, alpha), self.desc_border_color, 
            self.border_width_map.get(self.desc_border_strength.get(), 2), 
            self.desc_border_style.get(), 
            int(self.corner_radius_map.get(self.desc_corner_radius_choice.get(), 10)), 
            self.desc_shadow.get(), 
            desc_font, 
            desc_text_sc,
            gradient=(self.desc_pattern.get() == "Gradient"), 
            color2=self.desc_color2, 
            texture=self.desc_texture, 
            pattern=self.desc_pattern.get().lower() if self.desc_pattern.get() != "None" else None,
            text_outline=self.desc_text_outline.get(),
            text_color=self.desc_text_color
        )

    def update_tab_description(self, event=None):
        current = self.notebook.tab(self.notebook.select(), "text")
        descriptions = {
            "Paths": "v 1.2",
            "Background": "Plain color, screenshot dim, or Custom BG Image with Stretch/Zoom/Original/Tile modes + dim. All update live in Preview.",
            "Metadata Bar": "Full styling (colors, border style/radius/padding, gradient, patterns, text scale, transparency).",
            "Description": "Only available with gamelist.xml",
            "Additional Image": "Two independent additional PNG layers (transparency/shadow supported, shadows OFF by default). Drag to move in Preview. Center/Fit buttons per image. Layer order controllable.",
            "Physical Media": "Custom settings for disc art.",
            "Preview": "Pixel-accurate live view (CRT or 720p). Click elements to drag & reposition them live. Layer stacking order editable above.",
            "Optional Media": "How about adding back boxart or a title screen?"
        }
        self.tab_desc_label.config(text=descriptions.get(current, ""))

    @staticmethod
    def _hex(rgba):
        return "#%02x%02x%02x" % tuple(rgba[:3])

    def on_path_toggle(self, key):
        self.update_preview()

    def pick(self, key):
        if key == 'xml':
            p = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])
        else:
            p = filedialog.askdirectory(title=f"Select {key.upper()} Folder")
        if p:
            self.paths[key].set(p)
            self.update_preview()

    def load_additional_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.additional_image = path
            self.enable_additional.set(True)
            if hasattr(self, 'additional_label') and self.additional_label:
                fname = os.path.basename(path)
                self.additional_label.config(text=fname, foreground="#80ff80")
            messagebox.showinfo("Success", "Additional image loaded. Enable checkbox to use it.\nTransparency in PNGs is now handled correctly.")

    def load_additional2_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.additional2_image = path
            self.enable_additional2.set(True)
            if hasattr(self, 'additional2_label') and self.additional2_label:
                fname = os.path.basename(path)
                self.additional2_label.config(text=fname, foreground="#80ff80")
            messagebox.showinfo("Success", "Second additional image loaded. Enable its checkbox to use it.\nTransparency in PNGs is supported.")

    def load_custom_player_icon(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.ico")])
        if path:
            self.custom_player_icon = path
            if hasattr(self, 'custom_player_icon_label') and self.custom_player_icon_label:
                fname = os.path.basename(path)
                self.custom_player_icon_label.config(text=fname, foreground="#80ff80")
            messagebox.showinfo("Success", "Custom player icon loaded. Select 'Custom Icon' in Player Icon Style to use it.\nIt will be used for player count indicators in metadata bar.")

    def choose_bg(self):
        c = colorchooser.askcolor(color=self._hex(self.bg_color))[0]
        if c:
            self.bg_color = (*map(int, c), 255)
            self.bg_swatch.config(bg=self._hex(self.bg_color))
            self.update_preview()

    def choose_bg2(self):
        c = colorchooser.askcolor(color=self._hex(self.bg_color2))[0]
        if c:
            self.bg_color2 = (*map(int, c), 255)
            self.bg2_swatch.config(bg=self._hex(self.bg_color2))
            self.update_preview()

    def choose_bar(self):
        c = colorchooser.askcolor(color=self._hex((*self.bar_rgb, 255)))[0]
        if c:
            self.bar_rgb = tuple(map(int, c))
            self.bar_swatch.config(bg=self._hex((*self.bar_rgb, 255)))
            self.update_preview()

    def choose_bar_color2(self):
        c = colorchooser.askcolor(color=self._hex((*self.bar_color2[:3], 255)))[0]
        if c:
            self.bar_color2 = (*map(int, c), 255)
            if hasattr(self, "bar2_swatch"):
                self.bar2_swatch.config(bg=self._hex(self.bar_color2))
            self.update_preview()

    def choose_desc_color2(self):
        c = colorchooser.askcolor(color=self._hex((*self.desc_color2[:3], 255)))[0]
        if c:
            self.desc_color2 = (*map(int, c), 255)
            if hasattr(self, "desc2_swatch"):
                self.desc2_swatch.config(bg=self._hex(self.desc_color2))
            self.update_preview()

    def choose_border(self):
        c = colorchooser.askcolor(color=self._hex(self.border_color))[0]
        if c:
            self.border_color = (*map(int, c), 220)
            self.border_swatch.config(bg=self._hex(self.border_color))
            self.update_preview()

    def choose_desc(self):
        c = colorchooser.askcolor(color=self._hex((*self.desc_rgb, 255)))[0]
        if c:
            self.desc_rgb = tuple(map(int, c))
            self.desc_swatch.config(bg=self._hex((*self.desc_rgb, 255)))
            self.update_preview()

    def choose_text_color(self):
        c = colorchooser.askcolor(color=self._hex(self.text_color))[0]
        if c:
            self.text_color = tuple(map(int, c))
            self.text_swatch.config(bg=self._hex(self.text_color))
            self.update_preview()

    def choose_star_color(self):
        c = colorchooser.askcolor(color=self._hex(self.star_color))[0]
        if c:
            self.star_color = tuple(map(int, c))
            if hasattr(self, 'star_swatch') and self.star_swatch:
                self.star_swatch.config(bg=self._hex(self.star_color))
            self.update_preview()

    def choose_desc_border(self):
        c = colorchooser.askcolor(color=self._hex(self.desc_border_color))[0]
        if c:
            self.desc_border_color = (*map(int, c), 220)
            if hasattr(self, 'desc_border_swatch'):
                self.desc_border_swatch.config(bg=self._hex(self.desc_border_color))
            self.update_preview()

    def choose_desc_text_color(self):
        c = colorchooser.askcolor(color=self._hex(self.desc_text_color))[0]
        if c:
            self.desc_text_color = tuple(map(int, c))
            if hasattr(self, 'desc_text_swatch'):
                self.desc_text_swatch.config(bg=self._hex(self.desc_text_color))
            self.update_preview()

    def pick_font(self):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            self.custom_font = path
            messagebox.showinfo("Success", "Custom metadata font loaded. (Used in final render)")

    def pick_desc_font(self):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            self.desc_custom_font = path
            messagebox.showinfo("Success", "Custom description font loaded.")

    def load_bar_texture(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if path:
            self.bar_texture = path
            messagebox.showinfo("Success", "Bar texture loaded.")

    def unload_bar_texture(self):
        self.bar_texture = None
        messagebox.showinfo("Success", "Bar texture unloaded.")
        self.update_preview()

    def load_custom_bg(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.custom_bg_image = path
            self.use_custom_bg.set(True)
            fname = os.path.basename(path)
            self.custom_bg_label.config(text=fname, foreground="#80ff80")
            messagebox.showinfo("Success", "Custom background image loaded.\nUse 'Use Custom Background Image' checkbox to enable it.\nModes: Stretch (distort), Zoom/Cover (crops edges), Original (centered), Tile.")
            self.update_preview()

    def reset_defaults(self):
        self.plain_bg.set(False)
        self.use_custom_bg.set(False)
        self.custom_bg_image = None
        self.bg_image_mode.set("Stretch to Fill")
        for k in ["xml", "ss", "md", "roms", "optional_media"]:
            if k in self.path_enabled:
                self.path_enabled[k].set(k in ["xml", "ss", "md"])
            if k in self.paths:
                self.paths[k].set("")
        self.optimize.set(True)
        self.bg_color = (30, 30, 40, 255)
        self.bar_rgb = (25, 45, 90)
        self.bar_color2 = (35, 55, 105, 255)
        self.desc_color2 = (35, 55, 105, 255)
        self.border_color = (255, 255, 255, 220)
        self.desc_rgb = (25, 45, 90)
        self.desc_border_color = (255, 255, 255, 220)
        self.desc_text_color = (255, 255, 255)
        self.bg_color2 = (50, 50, 70, 255)
        self.text_scale_var.set(1.0)
        self.bar_alpha_pct.set(82)
        self.desc_font_scale.set(1.0)
        self.use_stars.set(False)  # default = stars (checkbox unchecked)
        self.display_rating_as_text.set(False)
        self.star_style.set("Classic Filled")
        self.star_color = (255, 215, 0)
        if hasattr(self, 'star_swatch') and self.star_swatch:
            self.star_swatch.config(bg=self._hex(self.star_color))
        self.star_spacing_mult.set(1.0)
        self.vertical_player_gap_mult.set(1.15)
        self.bar_shadow.set(True)
        self.media_shadow.set(True)
        self.use_description.set(False)
        self.desc_shadow.set(True)
        self.text_shadow.set(True)
        self.use_player_text.set(False)
        self.bar_vertical.set(False)
        self.vertical_labels.set(False)
        self.bg_pattern.set("None")
        self.bar_pattern.set("None")
        self.desc_pattern.set("None")
        self.desc_border_strength.set("Small")
        self.desc_border_style.set("Solid")
        self.desc_corner_radius_choice.set("Slight")
        self.desc_text_outline.set(True)
        self.border_strength.current(0)
        self.border_style.current(0)
        self.corner_radius_choice.current(1)
        self.padding_choice.current(1)
        self.dim_choice.current(1)
        self.media_size.current(1)
        self.media_custom_size.set(168)
        self.player_icon_style.set("Classic")
        self.res_mode.current(0)
        self.enable_additional.set(False)
        self.additional_scale.set(0.6)
        self.additional_alpha.set(100)
        self.additional_shadow.set(False)
        self.enable_additional2.set(False)
        self.additional2_image = None
        self.additional2_scale.set(0.5)
        self.additional2_alpha.set(80)
        self.additional2_shadow.set(False)
        self.enable_optional_media.set(False)
        self.hide_metadata.set(False)
        self.desc_alpha_pct.set(85)
        self.naming_mode.set("superstation")
        self.custom_suffix.set("-BG")
        if hasattr(self, 'opt_media_size'):
            self.opt_media_size.current(1)
        self.opt_media_custom_size.set(168)
        self.opt_media_x.set(30)
        self.opt_media_y.set(30)
        self.opt_media_shadow.set(True)
        self.opt_media_alpha.set(90)
        self.bg_swatch.config(bg=self._hex(self.bg_color))
        self.bg2_swatch.config(bg=self._hex(self.bg_color2))
        self.bar_swatch.config(bg=self._hex((*self.bar_rgb, 255)))
        self.border_swatch.config(bg=self._hex(self.border_color))
        self.desc_swatch.config(bg=self._hex((*self.desc_rgb, 255)))
        if hasattr(self, 'desc_border_swatch'):
            self.desc_border_swatch.config(bg=self._hex(self.desc_border_color))
        if hasattr(self, 'desc_text_swatch'):
            self.desc_text_swatch.config(bg=self._hex(self.desc_text_color))
        self.custom_font = None
        self.desc_custom_font = None
        self.bar_texture = None
        self.desc_texture = None
        self.additional_image = None
        self.custom_bg_image = None
        if hasattr(self, 'custom_bg_label'):
            self.custom_bg_label.config(text="No image selected", foreground="#a0a0b0")
        if hasattr(self, 'additional_label') and self.additional_label:
            self.additional_label.config(text="No image selected", foreground="#a0a0b0")
        if hasattr(self, 'additional2_label') and self.additional2_label:
            self.additional2_label.config(text="No image selected", foreground="#a0a0b0")
        self.custom_player_icon = None
        if hasattr(self, 'custom_player_icon_label') and self.custom_player_icon_label:
            self.custom_player_icon_label.config(text="No custom icon", foreground="#a0a0b0")
        self.apply_res_defaults()
        try:
            self.notebook.tab(2, state="normal", text="Metadata Bar")
            self.notebook.tab(3, state="normal", text="Description")
            if hasattr(self, 'opt_media_path_label'):
                self.opt_media_path_label.config(foreground="#a0a0b0")
        except:
            pass
        messagebox.showinfo("Defaults", "All settings reset to sensible defaults for current resolution.\nMetadata bar is centered by default.\nStars are now the DEFAULT rating style. Checkbox = Use Gauge instead.\nOptional Media and Additional Image shadows are OFF by default.")
        self.update_preview()

    def load_desc_texture(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if path:
            self.desc_texture = path
            messagebox.showinfo("Success", "Description texture loaded.")

    def copy_metadata_to_desc(self):
        self.desc_rgb = tuple(self.bar_rgb)
        if hasattr(self, 'desc_swatch'):
            self.desc_swatch.config(bg=self._hex((*self.desc_rgb, 255)))
        self.desc_border_color = tuple(self.border_color)
        if hasattr(self, 'desc_border_swatch'):
            self.desc_border_swatch.config(bg=self._hex(self.desc_border_color))
        self.desc_text_color = tuple(self.text_color)
        if hasattr(self, 'desc_text_swatch'):
            self.desc_text_swatch.config(bg=self._hex(self.desc_text_color))
        self.desc_border_strength.set(self.border_strength.get())
        self.desc_border_style.set(self.border_style.get())
        self.desc_corner_radius_choice.set(self.corner_radius_choice.get())
        self.desc_text_outline.set(self.text_shadow.get())
        self.desc_gradient.set(self.bar_gradient.get())
        self.desc_pattern.set(self.bar_pattern.get())
        self.desc_shadow.set(self.bar_shadow.get())
        messagebox.showinfo("Copied", "Description styling + border options copied from Metadata Bar for easy uniformity.")
        self.update_preview()

    def update_preview(self):
        try:
            is_720p = self.get_current_res() == "720p"
            target_W, target_H = (1280, 720) if is_720p else (640, 480)
            display_w = 560
            scale_factor = display_w / target_W
            
            preview_W = int(target_W * scale_factor)
            preview_H = int(target_H * scale_factor)
            
            self._preview_scale = scale_factor
            self._preview_target_size = (target_W, target_H)
            
            preview_img = Image.new("RGBA", (target_W, target_H), self.bg_color)
            
            if self.use_custom_bg.get() and self.custom_bg_image and os.path.exists(self.custom_bg_image):
                try:
                    cbg = Image.open(self.custom_bg_image).convert("RGBA")
                    mode = self.bg_image_mode.get()
                    if mode == "Stretch to Fill":
                        cbg = cbg.resize((target_W, target_H), Image.LANCZOS)
                    elif mode == "Zoom to Cover (crop)":
                        iw, ih = cbg.size
                        sc = max(target_W / iw, target_H / ih)
                        nw, nh = int(iw * sc), int(ih * sc)
                        cbg = cbg.resize((nw, nh), Image.LANCZOS)
                        l = max(0, (nw - target_W) // 2)
                        t = max(0, (nh - target_H) // 2)
                        cbg = cbg.crop((l, t, l + target_W, t + target_H))
                    elif mode == "Original Size (centered)":
                        canv = Image.new("RGBA", (target_W, target_H), self.bg_color)
                        ox = max(0, (target_W - cbg.width) // 2)
                        oy = max(0, (target_H - cbg.height) // 2)
                        canv.paste(cbg, (ox, oy), cbg if cbg.mode == "RGBA" else None)
                        cbg = canv
                    else:
                        canv = Image.new("RGBA", (target_W, target_H), self.bg_color)
                        tw, th = cbg.size
                        for yy in range(0, target_H, th):
                            for xx in range(0, target_W, tw):
                                canv.paste(cbg, (xx, yy), cbg if cbg.mode == "RGBA" else None)
                        cbg = canv
                    preview_img = cbg
                except Exception as e:
                    print("Custom BG preview error:", e)
            elif self.plain_bg.get():
                bg_pattern_raw = self.bg_pattern.get()
                bg_pattern = bg_pattern_raw.lower() if bg_pattern_raw != "None" else None
                is_gradient = bg_pattern_raw == "Gradient"
                effective_pattern = "checkerboard" if bg_pattern == "checkerboard" else bg_pattern
                if bg_pattern or is_gradient:
                    grad_dir = "vertical" if is_gradient else None
                    fill = create_fill_overlay((target_W, target_H), self.bg_color, self.bg_color2, grad_dir, None, effective_pattern)
                    preview_img.alpha_composite(fill)

            draw_funcs = {
                "additional": lambda: self._draw_additional_in_preview(preview_img, target_W, target_H, is_720p),
                "additional2": lambda: self._draw_additional2_in_preview(preview_img, target_W, target_H, is_720p),
                "optional_media": lambda: self._draw_optional_media_in_preview(preview_img, target_W, target_H, is_720p),
                "media": lambda: self._draw_media_placeholder_in_preview(preview_img, target_W, target_H, is_720p),
                "metadata": lambda: self._draw_metadata_in_preview(preview_img, target_W, target_H),
                "description": lambda: self._draw_description_in_preview(preview_img, target_W, target_H)
            }

            for layer in reversed(self.layer_order):
                if layer in draw_funcs:
                    try:
                        draw_funcs[layer]()
                    except Exception as e:
                        print(f"Layer draw error ({layer}):", e)

            display_img = preview_img.resize((preview_W, preview_H), Image.LANCZOS)
            
            preview_tk = ImageTk.PhotoImage(display_img)
            self.preview_canvas.delete("all")
            self.preview_canvas.config(width=preview_W, height=preview_H)
            self.preview_canvas.create_image(preview_W//2, preview_H//2, image=preview_tk)
            self.preview_img_ref = preview_tk
            
            mode_str = "720p (1280×720)" if is_720p else "CRT (640×480)"
            self.preview_info.config(text=f"Mode: {mode_str}  |  Preview is pixel-accurate scaled down.")
        except Exception as e:
            print("Preview error:", e)
            import traceback
            traceback.print_exc()

    def run(self):
        if not self.paths['out'].get():
            messagebox.showwarning("Missing", "Please select an Output folder!")
            return
        use_ss = self.path_enabled['ss'].get() and bool(self.paths['ss'].get())
        use_xml = self.path_enabled['xml'].get() and bool(self.paths['xml'].get())
        use_md = self.path_enabled['md'].get() and bool(self.paths['md'].get())
        use_roms = self.path_enabled['roms'].get() and bool(self.paths['roms'].get())
        use_desc = self.use_description.get() and use_xml
        
        if not use_ss and not self.plain_bg.get() and not use_roms and not (self.use_custom_bg.get() and self.custom_bg_image):
            messagebox.showwarning("Missing", "Select Screenshots, enable Plain/Custom Background, or use Games Folder!")
            return

        is_720p = self.get_current_res() == "720p"
        W, H = (1280, 720) if is_720p else (640, 480)
        
        games = load_gamelist(self.paths['xml'].get()) if use_xml else {}
        md_lookup = load_media_lookup(self.paths['md'].get()) if use_md else {}
        use_optional = self.path_enabled.get("optional_media") and self.path_enabled["optional_media"].get()
        opt_lookup = {}
        if use_optional and self.paths.get("optional_media"):
            opt_path = self.paths["optional_media"].get()
            if opt_path:
                opt_lookup = load_media_lookup(opt_path)

        if use_roms:
            rom_folder = self.paths['roms'].get()
            files = []
            for root, dirs, filenames in os.walk(rom_folder):
                for d in dirs:
                    files.append(os.path.join(root, d))
                for f in filenames:
                    files.append(os.path.join(root, f))
        elif use_ss:
            files = [os.path.join(self.paths['ss'].get(), f) for f in os.listdir(self.paths['ss'].get()) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        else:
            files = list(games.keys())

        self.progress["maximum"] = max(1, len(files))
        
        for i, file in enumerate(files):
            try:
                if os.path.isdir(file):
                    base_name = sanitize_stem(os.path.basename(file))
                else:
                    base_name = sanitize_stem(os.path.splitext(os.path.basename(file))[0])
                meta = games.get(base_name) if use_xml else None
                rom_name = base_name

                dim_factor = self.dim_map.get(self.dim_choice.get(), 0.70)
                if self.use_custom_bg.get() and self.custom_bg_image and os.path.exists(self.custom_bg_image):
                    try:
                        bg = Image.open(self.custom_bg_image).convert("RGBA")
                        mode = self.bg_image_mode.get()
                        if mode == "Stretch to Fill":
                            bg = bg.resize((W, H), Image.LANCZOS)
                        elif mode == "Zoom to Cover (crop)":
                            iw, ih = bg.size
                            scale = max(W / iw, H / ih)
                            new_w = int(iw * scale)
                            new_h = int(ih * scale)
                            bg = bg.resize((new_w, new_h), Image.LANCZOS)
                            left = max(0, (new_w - W) // 2)
                            top = max(0, (new_h - H) // 2)
                            bg = bg.crop((left, top, left + W, top + H))
                        elif mode == "Original Size (centered)":
                            canvas = Image.new("RGBA", (W, H), self.bg_color)
                            ox = max(0, (W - bg.width) // 2)
                            oy = max(0, (H - bg.height) // 2)
                            canvas.paste(bg, (ox, oy), bg if bg.mode == "RGBA" else None)
                            bg = canvas
                        else:
                            canvas = Image.new("RGBA", (W, H), self.bg_color)
                            tile_w, tile_h = bg.size
                            for y in range(0, H, tile_h):
                                for x in range(0, W, tile_w):
                                    canvas.paste(bg, (x, y), bg if bg.mode == "RGBA" else None)
                            bg = canvas
                        bg = ImageEnhance.Brightness(bg).enhance(dim_factor)
                    except Exception as e:
                        print(f"Custom BG error: {e}")
                        bg = Image.new("RGBA", (W, H), self.bg_color)
                elif self.plain_bg.get() or not use_ss:
                    bg = Image.new("RGBA", (W, H), self.bg_color)
                    bg_pattern_raw = self.bg_pattern.get()
                    bg_pattern = bg_pattern_raw.lower() if bg_pattern_raw != "None" else None
                    is_gradient = bg_pattern_raw == "Gradient"
                    effective_pattern = "checkerboard" if bg_pattern == "checkerboard" else bg_pattern
                    if bg_pattern or is_gradient:
                        fill_overlay = create_fill_overlay((W, H), self.bg_color, self.bg_color2, "vertical" if is_gradient else None, None, effective_pattern)
                        bg.alpha_composite(fill_overlay)
                else:
                    ss_path = file
                    if os.path.exists(ss_path):
                        bg = ImageOps.fit(Image.open(ss_path), (W, H)).convert("RGBA")
                        bg = ImageEnhance.Brightness(bg).enhance(dim_factor)
                    else:
                        bg = Image.new("RGBA", (W, H), self.bg_color)

                def _draw_meta_layer():
                    if not meta or self.hide_metadata.get(): return
                    bar_width = int(self.bar_w.get())
                    bar_width = max(300, min(bar_width, W - 60))
                    bx = int(self.bar_x_var.get())
                    by = int(self.bar_y_var.get())
                    bx = max(-300, min(bx, W + 100))
                    by = max(-100, min(by, H + 50))
                    draw_metadata_bar(
                        bg, bx, by, bar_width, meta,
                        (*self.bar_rgb, int(255 * self.bar_alpha_pct.get() / 100)), self.border_color, 
                        self.border_width_map.get(self.border_strength.get(), 2), 
                        self.border_style.get(), int(self.corner_radius_map.get(self.corner_radius_choice.get(), 10)), 
                        self.bar_shadow.get(), self.padding_map.get(self.padding_choice.get(), 1.0),
                        ImageFont.load_default(), not self.use_stars.get(), self.text_scale_var.get(),
                        gradient=(self.bar_pattern.get() == "Gradient"),
                        color2=self.bar_color2,
                        texture=self.bar_texture, 
                        pattern=self.bar_pattern.get().lower() if self.bar_pattern.get() not in ["None", "Gradient"] else None,
                        text_outline=self.text_shadow.get(), vertical=self.bar_vertical.get(), use_player_text=(self.player_icon_style.get() == "Players as Text"),
                        text_color=self.text_color,
                        custom_font_path=self.custom_font,
                        vertical_labels=self.vertical_labels.get(),
                        player_icon_style=self.player_icon_style.get(),
                        bar_height=self.bar_height_var.get(),
                        custom_player_icon_path=self.custom_player_icon,
                        display_rating_as_text=self.display_rating_as_text.get(),
                        star_style=self.star_style.get(),
                        star_color=self.star_color,
                        star_spacing_mult=self.star_spacing_mult.get(),
                        vertical_player_gap_mult=self.vertical_player_gap_mult.get()
                    )

                def _draw_desc_layer():
                    if not (self.use_description.get() and meta and meta.get("description")): return
                    try:
                        if self.desc_custom_font and os.path.exists(self.desc_custom_font):
                            fpath = self.desc_custom_font
                        else:
                            fpath = resource_path("DejaVuSans-Bold.ttf")
                        dsc = self.desc_font_scale.get()
                        desc_font_size = max(8, int(12 * dsc))
                        desc_font = ImageFont.truetype(fpath, desc_font_size)
                    except Exception:
                        desc_font = ImageFont.load_default()
                    alpha = int(255 * self.desc_alpha_pct.get() / 100)
                    draw_description_box(
                        bg, int(self.desc_x.get()), int(self.desc_y.get()), 
                        int(self.desc_w.get()), int(self.desc_h.get()), meta.get("description"), 
                        (*self.desc_rgb, alpha), self.desc_border_color, 
                        self.border_width_map.get(self.desc_border_strength.get(), 2), 
                        self.desc_border_style.get(), int(self.corner_radius_map.get(self.desc_corner_radius_choice.get(), 10)), 
                        self.desc_shadow.get(), desc_font, self.desc_font_scale.get(),
                        gradient=(self.desc_pattern.get() == "Gradient"), color2=self.desc_color2, texture=self.desc_texture, 
                        pattern=self.desc_pattern.get().lower() if self.desc_pattern.get() != "None" else None,
                        text_outline=self.desc_text_outline.get(),
                        text_color=self.desc_text_color
                    )

                def _draw_physical_layer():
                    if not use_md: return
                    media_path = find_media_image(md_lookup, meta, base_name)
                    if not media_path: return
                    try:
                        d = Image.open(media_path).convert("RGBA")
                        media_size = int(self.media_custom_size.get() * (1.8 if is_720p else 1.0))
                        d.thumbnail((media_size, media_size), Image.LANCZOS)
                        mx = W - d.width - int(self.media_x.get())
                        my = H - d.height - int(self.media_y.get())
                        if self.media_shadow.get():
                            alpha_ch = d.split()[-1] if d.mode == 'RGBA' else None
                            shadow_layer = Image.new("RGBA", d.size, (0, 0, 0, 160))
                            if alpha_ch: shadow_layer.putalpha(alpha_ch)
                            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(5 if is_720p else 3))
                            shadow_canvas = Image.new("RGBA", bg.size, (0, 0, 0, 0))
                            shadow_canvas.paste(shadow_layer, (mx + 8, my + 8), shadow_layer)
                            bg.alpha_composite(shadow_canvas)
                        bg.alpha_composite(d, (mx, my))
                    except Exception as e:
                        print(f"Media load error for {file}: {e}")

                def _draw_optional_layer():
                    if not (self.enable_optional_media.get() and opt_lookup): return
                    opt_path = find_media_image(opt_lookup, meta, base_name)
                    if not opt_path: return
                    try:
                        d = Image.open(opt_path).convert("RGBA")
                        media_size = int(self.opt_media_custom_size.get() * (1.8 if is_720p else 1.0))
                        d.thumbnail((media_size, media_size), Image.LANCZOS)
                        mx = W - d.width - int(self.opt_media_x.get())
                        my = H - d.height - int(self.opt_media_y.get())
                        if self.opt_media_shadow.get():
                            alpha_ch = d.split()[-1] if d.mode == 'RGBA' else None
                            shadow_layer = Image.new("RGBA", d.size, (0, 0, 0, 150))
                            if alpha_ch: shadow_layer.putalpha(alpha_ch)
                            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(5 if is_720p else 3))
                            shadow_canvas = Image.new("RGBA", bg.size, (0, 0, 0, 0))
                            shadow_canvas.paste(shadow_layer, (mx + 8, my + 8), shadow_layer)
                            bg.alpha_composite(shadow_canvas)
                        if self.opt_media_alpha.get() < 100:
                            r, g, b, a = d.split()
                            a = a.point(lambda p: int(p * (self.opt_media_alpha.get() / 100.0)))
                            d = Image.merge("RGBA", (r, g, b, a))
                        bg.alpha_composite(d, (mx, my))
                    except Exception as e:
                        print(f"Optional media load error for {file}: {e}")

                def _draw_add_layer():
                    if not (self.enable_additional.get() and self.additional_image): return
                    try:
                        add_img = Image.open(self.additional_image).convert("RGBA")
                        add_w = int(add_img.width * self.additional_scale.get())
                        add_h = int(add_img.height * self.additional_scale.get())
                        add_img = add_img.resize((add_w, add_h), Image.LANCZOS)
                        ax = int(self.additional_x.get())
                        ay = int(self.additional_y.get())
                        alpha = self.additional_alpha.get()
                        if self.additional_shadow.get():
                            shadow = Image.new("RGBA", (add_w + 12, add_h + 12), (0,0,0,0))
                            sd = ImageDraw.Draw(shadow)
                            sd.rounded_rectangle([5,5,add_w+5,add_h+5], radius=8, fill=(0,0,0, int(115 * alpha / 100)))
                            shadow = shadow.filter(ImageFilter.GaussianBlur(5))
                            bg.alpha_composite(shadow, (ax, ay))
                        if alpha < 100:
                            r, g, b, a = add_img.split()
                            a = a.point(lambda p: int(p * (alpha / 100.0)))
                            add_img = Image.merge("RGBA", (r, g, b, a))
                        bg.alpha_composite(add_img, (ax, ay))
                    except Exception as e:
                        print(f"Additional image error for {file}: {e}")

                def _draw_add2_layer():
                    if not (self.enable_additional2.get() and self.additional2_image): return
                    try:
                        add_img = Image.open(self.additional2_image).convert("RGBA")
                        add_w = int(add_img.width * self.additional2_scale.get())
                        add_h = int(add_img.height * self.additional2_scale.get())
                        add_img = add_img.resize((add_w, add_h), Image.LANCZOS)
                        ax = int(self.additional2_x.get())
                        ay = int(self.additional2_y.get())
                        alpha = self.additional2_alpha.get()
                        if self.additional2_shadow.get():
                            shadow = Image.new("RGBA", (add_w + 12, add_h + 12), (0,0,0,0))
                            sd = ImageDraw.Draw(shadow)
                            sd.rounded_rectangle([5,5,add_w+5,add_h+5], radius=8, fill=(0,0,0, int(115 * alpha / 100)))
                            shadow = shadow.filter(ImageFilter.GaussianBlur(5))
                            bg.alpha_composite(shadow, (ax, ay))
                        if alpha < 100:
                            r, g, b, a = add_img.split()
                            a = a.point(lambda p: int(p * (alpha / 100.0)))
                            add_img = Image.merge("RGBA", (r, g, b, a))
                        bg.alpha_composite(add_img, (ax, ay))
                    except Exception as e:
                        print(f"Additional2 image error for {file}: {e}")

                _layer_drawers = {
                    "description": _draw_desc_layer,
                    "metadata": _draw_meta_layer,
                    "media": _draw_physical_layer,
                    "optional_media": _draw_optional_layer,
                    "additional2": _draw_add2_layer,
                    "additional": _draw_add_layer,
                }
                for lyr in reversed(self.layer_order):
                    if lyr in _layer_drawers:
                        _layer_drawers[lyr]()

                out_name = base_name
                mode = self.naming_mode.get()
                if mode == "superstation":
                    suffix = "-BG.png"
                elif mode == "esde":
                    suffix = ".png"
                else:
                    suf = (self.custom_suffix.get() or "").strip()
                    if not suf:
                        suffix = ".png"
                    else:
                        if not suf.endswith(".png"):
                            suffix = suf + ".png"
                        else:
                            suffix = suf
                out_path = os.path.join(self.paths['out'].get(), out_name + suffix)
                if self.optimize.get():
                    bg = bg.convert("P", palette=Image.ADAPTIVE, colors=128)
                    bg.save(out_path, "PNG", optimize=True, compress_level=9)
                else:
                    bg.save(out_path, "PNG", compress_level=6)

                self.progress["value"] = i + 1
                self.update_idletasks()
            except Exception as e:
                print(f"Error processing {file}: {e}")

        messagebox.showinfo("Success", f"Generated {len(files)} background images!")

if __name__ == "__main__":
    app = App()
    app.mainloop()
