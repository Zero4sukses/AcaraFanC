from datetime import datetime
import json
import os
import requests

OUTPUT_M3U = "FanClangsung.m3u"

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
    """Resolver token/HLS untuk link pemutaran .m3u8 asli"""
    stream_url = f"https://lex-prod.fancode.com/i/{match_id}/index.m3u8"
    return stream_url

def is_stream_active(url):
    """Dead-Link Checker: Memeriksa apakah link m3u8 masih aktif"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
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

def generate_cleaned_m3u():
    matches = fetch_fancode_api()
    
    # Header M3U dengan dukungan logo eksternal (tvg-logo / epg)
    m3u_content = '#EXTM3U x-tvg-url=""\n'
    valid_count = 0
    filtered_count = 0
    
    for match in matches:
        match_id = match.get("id")
        title = match.get("name", "FanCode Match")
        tour = match.get("tour", {}).get("name", "General Sports")
        status = match.get("status_string", "LIVE")
        
        # Penentuan Kategori Grup Olahraga
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
        
        # Contoh Logo Otomatis (Mengambil logo default FanCode atau kustom)
        logo_url = f"https://images.fancode.com/events/{match_id}/logo.png"
        
        print(f"Memeriksa status link untuk: {title}...")
        if is_stream_active(stream_url):
            m3u_content += f'#EXTINF:-1 tvg-id="{match_id}" tvg-name="{channel_title}" tvg-logo="{logo_url}" tvg-group="{sport_category}",{channel_title}\n'
            m3u_content += f'{stream_url}\n'
            valid_count += 1
            print(" -> [AKTIF] Ditambahkan ke playlist.")
        else:
            filtered_count += 1
            print(" -> [OFFLINE/MATI] Dilewati.")

    if valid_count == 0:
        m3u_content += '#EXTINF:-1 tvg-group="FanCode Info",[INFO] Tidak ada siaran aktif saat ini\n'
        m3u_content += 'https://raw.githubusercontent.com/username/repo/main/offline.m3u8\n'

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content)
        
    print(f"\nSelesai! {valid_count} channel aktif dimasukkan, {filtered_count} channel mati disaring.")

if __name__ == "__main__":
    generate_cleaned_m3u()
