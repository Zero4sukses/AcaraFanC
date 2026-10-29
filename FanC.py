from datetime import datetime
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont

OUTPUT_M3U = "FanClangsung.m3u"
OUTPUT_IMAGE = "jadwal_fanc.png"

def fetch_fancode_api():
    """Mengambil data pertandingan aktif dari API internal FanCode"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.fancode.com/",
        "Accept": "application/json, text/plain, */*"
    }
    
    api_url = "https://api.fancode.com/v1/content/matches?status=live,upcoming"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get("body", {}).get("matches", [])
    except Exception as e:
        print(f"Gagal terhubung ke API FanCode: {e}")
        
    return []

def extract_stream_url(match_id):
    stream_url = f"https://lex-prod.fancode.com/i/{match_id}/index.m3u8"
    return stream_url

def is_stream_active(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        if response.status_code in [200, 301, 302]:
            return True
        response_get = requests.get(url, headers=headers, timeout=5)
        if response_get.status_code == 200:
            return True
    except Exception:
        pass
    return False

def generate_schedule_image(matches_data):
    """Membuat file gambar (PNG) berisi daftar jadwal siaran aktif"""
    img_width = 1200
    row_height = 70
    header_height = 120
    footer_height = 60
    
    # Filter hanya mengambil match yang valid/aktif untuk ditampilkan di gambar
    active_matches = [m for m in matches_data if is_stream_active(extract_stream_url(m.get("id")))]
    
    total_rows = max(len(active_matches), 1)
    img_height = header_height + (total_rows * row_height) + footer_height
    
    # Buat kanvas gambar dengan latar belakang gelap elegan (Gaya IPTV / Esports)
    img = Image.new("RGB", (img_width, img_height), color="#121824")
    draw = ImageDraw.Draw(img)
    
    # Load Font (Menggunakan default font bawaan pillow atau fallback aman)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        font_header = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        font_text = ImageFont.truetype("DejaVuSans.ttf", 18)
    except IOError:
        font_title = font_header = font_text = ImageFont.load_default()

    # Gambar Header
    draw.rectangle([0, 0, img_width, header_height], fill="#1E293B")
    draw.text((40, 30), "SCHEDULE SIARAN FANCODE LIVE", fill="#38BDF8", font=font_title)
    current_time_str = datetime.now().strftime("%d %b %Y | %H:%M WIB")
    draw.text((40, 75), f"Pembaruan Otomatis: {current_time_str}", fill="#94A3B8", font=font_header)
    
    # Header Kolom Tabel
    y_offset = header_height + 15
    draw.rectangle([30, y_offset, img_width - 30, y_offset + 40], fill="#334155")
    draw.text((50, y_offset + 10), "STATUS", fill="#F8FAFC", font=font_header)
    draw.text((180, y_offset + 10), "KATEGORI / TURNAMEN", fill="#F8FAFC", font=font_header)
    draw.text((650, y_offset + 10), "NAMA PERTANDINGAN", fill="#F8FAFC", font=font_header)
    
    y_offset += 55
    
    if not active_matches:
        draw.text((50, y_offset + 20), "Tidak ada siaran aktif / live saat ini.", fill="#EF4444", font=font_text)
    else:
        for idx, match in enumerate(active_matches):
            status = match.get("status_string", "LIVE")
            tour = match.get("tour", {}).get("name", "General")
            title = match.get("name", "Match")
            
            # Warna latar baris selang-seling
            row_bg = "#1E293B" if idx % 2 == 0 else "#0F172A"
            draw.rectangle([30, y_offset, img_width - 30, y_offset + 55], fill=row_bg)
            
            # Status Badge warna hijau/merah
            status_color = "#22C55E" if status.upper() == "LIVE" else "#EAB308"
            draw.text((50, y_offset + 16), f"[{status}]", fill=status_color, font=font_text)
            
            # Potong teks jika terlalu panjang
            tour_display = (tour[:35] + '..') if len(tour) > 35 else tour
            title_display = (match.get("name", "")[:45] + '..') if len(match.get("name", "")) > 45 else match.get("name", "")
            
            draw.text((180, y_offset + 16), tour_display, fill="#E2E8F0", font=font_text)
            draw.text((650, y_offset + 16), title_display, fill="#38BDF8", font=font_text)
            
            y_offset += row_height

    # Footer Gambar
    footer_y = img_height - 40
    draw.text((40, footer_y), "AcaraFanC Automation Bot - Powered by GitHub Actions", fill="#64748B", font=font_text)
    
    # Simpan gambar
    img.save(OUTPUT_IMAGE, "PNG")
    print(f"File gambar jadwal berhasil dibuat: {OUTPUT_IMAGE}")

def generate_cleaned_m3u():
    matches = fetch_fancode_api()
    m3u_content = '#EXTM3U x-tvg-url=""\n'
    valid_count = 0
    
    for match in matches:
        match_id = match.get("id")
        title = match.get("name", "FanCode Match")
        tour = match.get("tour", {}).get("name", "General Sports")
        status = match.get("status_string", "LIVE")
        
        sport_category = "FanCode Sports"
        tour_lower = tour.lower()
        if "football" in tour_lower or "soccer" in tour_lower:
            sport_category = "⚽ FanCode Football"
        elif "tennis" in tour_lower:
            sport_category = "🎾 FanCode Lawn Tennis"
        elif "cricket" in tour_lower:
            sport_category = "🏏 FanCode Cricket"
        else:
            sport_category = "📺 FanCode Live Lainnya"
            
        channel_title = f"[{status}] {tour} - {title}"
        stream_url = extract_stream_url(match_id)
        logo_url = f"https://images.fancode.com/events/{match_id}/logo.png"
        
        if is_stream_active(stream_url):
            m3u_content += f'#EXTINF:-1 tvg-id="{match_id}" tvg-name="{channel_title}" tvg-logo="{logo_url}" tvg-group="{sport_category}",{channel_title}\n'
            m3u_content += f'{stream_url}\n'
            valid_count += 1

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content)
        
    print(f"Playlist {OUTPUT_M3U} berhasil diperbarui ({valid_count} channel).")
    
    # Panggil fungsi pembuat gambar jadwal
    generate_schedule_image(matches)

if __name__ == "__main__":
    generate_cleaned_m3u()
