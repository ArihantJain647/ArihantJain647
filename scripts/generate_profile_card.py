#!/usr/bin/env python3
"""
Generates neofetch/terminal-style profile cards (profile_card_dark.svg & profile_card_light.svg)
for Arihant Jain's GitHub profile README.
- Left column: High-tech ASCII digital avatar / circuitry art
- Right column: Real-time developer metadata, stats, tech stack, and social links
"""

import os
import sys
import io
import glob
import datetime
import urllib.request
import json
from PIL import Image, ImageOps, ImageFilter

USERNAME = os.environ.get("GH_USERNAME", "ArihantJain647")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

ACCENT_DARK = "#38bdf8"    # Modern Sky / Cyan Blue for dark mode
ACCENT_LIGHT = "#0284c7"   # High-contrast Sky Blue for light mode
ASCII_RAMP = "@80GCLft1i;:,. "  # 15 levels: dense to sparse
ASCII_WIDTH = 75
LOCAL_IMAGE_GLOB = os.path.join(os.path.dirname(__file__), "avatar.*")


def fetch_user_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    try:
        req = urllib.request.Request(f"https://api.github.com/users/{USERNAME}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: Could not fetch user data online ({e}), using verified fallback.")
        return {
            "login": "ArihantJain647",
            "name": "Arihant Jain",
            "followers": 1,
            "following": 2,
            "public_repos": 5,
            "created_at": "2025-03-29T10:50:41Z",
            "avatar_url": "https://avatars.githubusercontent.com/u/205419399?v=4"
        }


def load_source_image_bytes(fallback_url):
    matches = glob.glob(LOCAL_IMAGE_GLOB)
    if matches:
        print(f"Using local avatar: {matches[0]}")
        with open(matches[0], "rb") as f:
            return f.read()
    try:
        req = urllib.request.Request(fallback_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"Warning: could not fetch avatar ({e})")
        # generate a fallback blank square
        img = Image.new("RGB", (100, 100), color=(30, 41, 59))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def dither_to_ascii(img_L, ramp):
    width, height = img_L.size
    levels = len(ramp)
    step = 255.0 / (levels - 1)
    if hasattr(img_L, "get_flattened_data"):
        pixels = list(img_L.get_flattened_data())
    else:
        pixels = list(img_L.getdata())
    grid = [[float(v) for v in pixels[y * width:(y + 1) * width]] for y in range(height)]

    lines = []
    for y in range(height):
        row_chars = []
        for x in range(width):
            old_val = grid[y][x]
            idx = min(levels - 1, max(0, round(old_val / step)))
            row_chars.append(ramp[idx])
            err = old_val - idx * step
            if x + 1 < width:
                grid[y][x + 1] += err * 7 / 16
            if y + 1 < height:
                if x > 0:
                    grid[y + 1][x - 1] += err * 3 / 16
                grid[y + 1][x] += err * 5 / 16
                if x + 1 < width:
                    grid[y + 1][x + 1] += err * 1 / 16
        lines.append("".join(row_chars))
    return lines


def image_to_ascii(image_bytes, width=ASCII_WIDTH):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        flat = Image.new("RGB", img.size, "white")
        flat.paste(img, mask=img.split()[3])
        img = flat
    else:
        img = img.convert("RGB")
    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    aspect_correction = 0.48
    height = max(1, int(img.height * (width / img.width) * aspect_correction))
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3))
    img = img.resize((width, height), Image.LANCZOS)
    return dither_to_ascii(img, ASCII_RAMP)


def xml_escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(ascii_lines, stats_lines, theme):
    is_dark = theme == "dark"
    bg = "#0d1117" if is_dark else "#ffffff"
    fg = "#e6edf3" if is_dark else "#1f2328"
    dim = "#7d8590" if is_dark else "#656d76"
    accent = ACCENT_DARK if is_dark else ACCENT_LIGHT
    border = "#30363d" if is_dark else "#d0d7de"

    ascii_font_size = 9
    ascii_line_height = 11.2
    ascii_char_width = 5.5
    pad = 22

    stats_font_size = 12.5
    stats_line_height = 16.5

    ascii_col_width = max(len(l) for l in ascii_lines) * ascii_char_width
    stats_x = pad + ascii_col_width + 36

    ascii_block_height = pad + len(ascii_lines) * ascii_line_height
    stats_block_height = pad + len(stats_lines) * stats_line_height
    height = int(max(ascii_block_height, stats_block_height) + 16)
    width = int(stats_x + 550)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Fira Code, SFMono-Regular, Consolas, Menlo, monospace">',
        f'<rect width="100%" height="100%" fill="{bg}" rx="12" stroke="{border}" stroke-width="1.5"/>',
    ]

    # Draw ASCII Art column
    y = pad + 10
    for line in ascii_lines:
        svg.append(
            f'<text x="{pad}" y="{y}" font-size="{ascii_font_size}" fill="{accent}" '
            f'xml:space="preserve">{xml_escape(line)}</text>'
        )
        y += ascii_line_height

    # Draw Stats column
    y = pad + 10
    for line in stats_lines:
        if line.startswith("§"):  # Section header
            content = line[1:]
            svg.append(
                f'<text x="{stats_x}" y="{y}" font-size="{stats_font_size}" fill="{accent}" '
                f'font-weight="bold">{xml_escape(content)}</text>'
            )
        elif ":" in line:
            label, _, value = line.partition(":")
            svg.append(
                f'<text x="{stats_x}" y="{y}" font-size="{stats_font_size}">'
                f'<tspan fill="{dim}">{xml_escape(label)}:</tspan> '
                f'<tspan fill="{fg}" font-weight="500">{xml_escape(value.strip())}</tspan></text>'
            )
        else:
            svg.append(
                f'<text x="{stats_x}" y="{y}" font-size="{stats_font_size}" fill="{fg}">{xml_escape(line)}</text>'
            )
        y += stats_line_height

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    user = fetch_user_data()
    image_bytes = load_source_image_bytes(user.get("avatar_url", ""))
    ascii_lines = image_to_ascii(image_bytes)

    # Compute account age
    created_dt = datetime.datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    account_age_days = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - created_dt).days
    years, rem_days = divmod(account_age_days, 365)
    months = rem_days // 30

    stats_lines = [
        f"§{USERNAME}@github  " + "-" * 38,
        "Name: Arihant Jain",
        "Role: AI Engineer & Builder",
        f"Account Age: {years}y {months}m",
        "Followers: " + str(user.get("followers", 1)),
        "",
        "§Education & Experience  " + "-" * 31,
        "Education: Arya College of Eng. (B.Tech CS & AI, 3rd Year)",
        "Experience: AI Intern @ Atmousmind Technologies Pvt. Ltd.",
        "",
        "§Tech Stack & Core Tools  " + "-" * 30,
        "Languages: Python, C, C++, JavaScript, TypeScript",
        "Technologies: Docker, GitHub, APIs, Vite, Tailwind CSS",
        "AI Tooling: Claude, Antigravity, Kiro, Cursor",
        "",
        "§Featured Projects  " + "-" * 36,
        "AI Agents: VibeSite (AI Website Vibecoder)",
        "AI Systems: PromptCV (Resume & ATS Optimizer w/ Gemini)",
        "Desktop AI: Excel AI Test Bench (Electron Tool-Calling)",
        "Automation: Scan2Serve (Contactless QR Restaurant App)",
        "",
        "§Contact & Socials  " + "-" * 36,
        "GitHub: github.com/" + USERNAME,
        "LinkedIn: linkedin.com/in/arihantjain98872",
        "Email: arihantjain98872@gmail.com",
    ]

    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for theme in ("dark", "light"):
        svg = render_svg(ascii_lines, stats_lines, theme)
        out_path = os.path.join(out_dir, f"profile_card_{theme}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Generated {out_path}")


if __name__ == "__main__":
    main()
