import os
import sys
import subprocess
import shutil
import http.server
import socketserver
import json
import urllib.parse


def initialize_app_assets():
    print("\n⏳ [Init] Checking application assets... Please wait.")
    base_dir = os.path.expanduser("~")
    app_data_dir = os.path.join(base_dir, "downloads", "app_assets")
    if not os.path.exists(app_data_dir):
        os.makedirs(app_data_dir)
    print("✅ [Init] Mega Dashboard System Ready!")


def get_ass_colors(text_hex, bg_hex):
    colors_map = {
        "#00ff00": "00FF00",
        "#ffff00": "00FFFF",
        "#00ffff": "FFFF00",
        "#ffffff": "FFFFFF",
        "#ff3333": "3333FF",
        "#d4af37": "37AFD4",
        "#ff007f": "7F00FF",
        "#000000": "000000",
    }

    primary = colors_map.get(text_hex, "FFFFFF")
    back_color = "000000"
    border_style = "1"

    if bg_hex == "none":
        back_color = "000000"
        border_style = "1"
    elif bg_hex == "rgba(0,0,0,0.6)":
        back_color = "80000000"
        border_style = "3"
    elif bg_hex == "#000000":
        back_color = "00000000"
        border_style = "3"
    elif bg_hex == "#ff3333":
        back_color = "003333FF"
        border_style = "3"
    elif bg_hex == "#0000ff":
        back_color = "00FF0000"
        border_style = "3"
    elif bg_hex == "#ffffff":
        back_color = "00FFFFFF"
        border_style = "3"

    return primary, back_color, border_style


# Global working directories
base_dir = os.path.expanduser("~")
shorts_dir = os.path.join(base_dir, "downloads", "shorts")


class SmartShortsHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        root = shorts_dir
        parsed = urllib.parse.urlparse(path)
        path = parsed.path
        path = urllib.parse.unquote(path)
        parts = path.split('/')
        parts = [p for p in parts if p != '']
        return os.path.join(root, *parts)

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            if not os.path.exists(os.path.join(shorts_dir, "index.html")):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(get_setup_html().encode('utf-8'))
                return
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = json.loads(post_data.decode('utf-8'))

        if self.path == '/process':
            url = params.get('url', '').strip()
            api_key = params.get('apiKey', '').strip()
            try:
                clip_duration = int(params.get('duration', 30))
            except Exception:
                clip_duration = 30
            try:
                max_clips = int(params.get('maxClips', 3))
            except Exception:
                max_clips = 3

            if not url or not api_key:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Missing URL or API Key"}).encode('utf-8'))
                return

            print(f"\n🚀 [Web Engine] Starting Process for URL: {url}")
            success = run_backend_processing(url, api_key, clip_duration, max_clips)

            if success:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Processing failed. Check terminal."}).encode('utf-8'))
            return

        if self.path == '/export':
            clip_id = params.get('clipId', '1')
            bottom_pos = int(params.get('position', 30))
            text_color = params.get('textColor', '#00ff00')
            bg_color = params.get('bgColor', 'none')
            fs_num = int(params.get('fontSize', 26))

            print(f"\n🎬 [Export Engine] Baking Video for Clip {clip_id} with custom Colors & Font Size...")

            local_json = os.path.join(shorts_dir, f"viral_short_{clip_id}.json")
            local_ass = os.path.join(shorts_dir, f"final_export_{clip_id}.ass")
            temp_clip = os.path.join(base_dir, "downloads", f"temp_clip_{clip_id}.mp4")
            final_exported_video = os.path.join(shorts_dir, f"final_tiktok_ready_{clip_id}.mp4")

            margin_v = int((bottom_pos / 100) * 1280)
            ass_primary, ass_back, border_style = get_ass_colors(text_color, bg_color)

            header = (
                "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"Style: Default,Arial,{fs_num},&H00FFFFFF,&H000000FF,&H00000000,&H{ass_back},-1,0,0,0,100,100,0,0,{border_style},3,0,2,30,30,{margin_v},1\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            )

            def format_ass_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                cs = int((seconds % 1) * 100)
                return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

            try:
                with open(local_json, "r", encoding="utf-8") as f:
                    captions_data = json.load(f)

                ass_content = header
                for c in captions_data:
                    for w in c["words"]:
                        start_time = format_ass_time(w["start"])
                        end_time = format_ass_time(w["end"])
                        word_text = f"{w['text']}"
                        ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\1c&H{ass_primary}&}}{word_text}\n"

                with open(local_ass, "w", encoding="utf-8") as f:
                    f.write(ass_content)

                vf_filter = (
                    "split[v1][v2];"
                    "[v1]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=luma_radius=15:luma_power=2[bg];"
                    "[v2]scale=720:-1:force_original_aspect_ratio=decrease[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,subtitles='{local_ass}'"
                )

                ffmpeg_cmd = f"ffmpeg -y -i '{temp_clip}' -vf \"{vf_filter}\" -c:v libx264 -crf 22 -preset ultrafast -pix_fmt yuv420p -c:a aac -ac 2 -b:a 128k '{final_exported_video}'"
                subprocess.run(ffmpeg_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "video": f"final_tiktok_ready_{clip_id}.mp4"}).encode('utf-8'))
                print(f"✅ [Export Engine] Clip {clip_id} Saved Successfully!")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

    def log_message(self, format, *args):
        pass


def get_best_highlights(url, max_clips):
    import yt_dlp
    print(f"\n🧠 [1/3] Fetching data... Searching for top {max_clips} viral moments...")
    ydl_opts = {'quiet': True, 'no_warnings': True, 'logger': None}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        heatmap = info.get('heatmap')
        duration = info.get('duration', 0)

    if heatmap:
        sorted_moments = sorted(heatmap, key=lambda x: x.get('value', 0), reverse=True)
        highlights = []
        for moment in sorted_moments:
            start = moment.get('start_time', 0)
            if 20 < start < (duration - 100):
                if not any(abs(start - h) < 60 for h in highlights):
                    highlights.append(start)
                if len(highlights) >= max_clips:
                    return highlights
        return highlights
    return [duration / 3, duration / 2][:max_clips]


def generate_cloud_captions(video_path, json_output_path, api_key):
    print("☁️ [3/3] Fetching Word-Level Perfect Subtitles from Groq AI...")
    temp_audio = video_path.replace('.mp4', '.mp3')
    extract_audio_cmd = [
        'ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'mp3', '-ar', '16000', '-ac', '1', temp_audio
    ]
    subprocess.run(extract_audio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(temp_audio):
        return False

    curl_cmd = (
        f'curl -s -X POST "https://api.groq.com/openai/v1/audio/transcriptions" '
        f'-H "Authorization: Bearer {api_key}" '
        f'-H "Content-Type: multipart/form-data" '
        f'-F "file=@{temp_audio}" '
        f'-F "model=whisper-large-v3" '
        f'-F "response_format=verbose_json"'
    )

    try:
        result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        data = json.loads(result.stdout)
        segments = data.get("segments", [])

        timed_captions = []
        for seg in segments:
            words_list = seg.get("words", [])
            if words_list:
                for i in range(0, len(words_list), 4):
                    chunk_words = words_list[i:i+4]
                    line_words = []
                    for w in chunk_words:
                        line_words.append({
                            "text": w["word"].strip(),
                            "start": w["start"],
                            "end": w["end"]
                        })
                    timed_captions.append({
                        "start": chunk_words[0]["start"],
                        "end": chunk_words[-1]["end"],
                        "words": line_words
                    })
            else:
                text_chunk = seg.get("text", "").strip()
                start_s = seg.get("start", 0.0)
                end_s = seg.get("end", 1.0)
                timed_captions.append({
                    "start": start_s,
                    "end": end_s,
                    "words": [{"text": text_chunk, "start": start_s, "end": end_s}]
                })

        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(timed_captions, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f" ❌ Caption Error: {e}")
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        return False


def run_backend_processing(url, api_key, clip_duration, max_clips):
    global shorts_dir
    if os.path.exists(shorts_dir):
        shutil.rmtree(shorts_dir)
    os.makedirs(shorts_dir, exist_ok=True)

    try:
        moments = get_best_highlights(url, max_clips)

        import yt_dlp
        ydl_opts = {'format': 'best[ext=mp4]/best', 'quiet': True, 'no_warnings': True, 'logger': None}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=False)
            stream_url = meta['url']

        count = 1
        for start_time in moments:
            local_json = os.path.join(shorts_dir, f"viral_short_{count}.json")
            temp_clip = os.path.join(base_dir, "downloads", f"temp_clip_{count}.mp4")
            if os.path.exists(temp_clip):
                os.remove(temp_clip)

            print(f"\n⚡ [2/3] Extracting segment {count}...")
            ffmpeg_stream_cmd = [
                'ffmpeg', '-y', '-ss', str(start_time), '-i', stream_url,
                '-t', str(clip_duration), '-c', 'copy', temp_clip
            ]
            subprocess.run(ffmpeg_stream_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            if not os.path.exists(temp_clip):
                continue

            generate_cloud_captions(temp_clip, local_json, api_key)

            final_short = os.path.join(shorts_dir, f"viral_short_{count}.mp4")
            print(f"🎬 Generating Clean Preview Canvas for Clip {count}...")

            vf_filter = (
                "split[v1][v2];"
                "[v1]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=luma_radius=15:luma_power=2[bg];"
                "[v2]scale=720:-1:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )

            ffmpeg_cmd = f"ffmpeg -y -i '{temp_clip}' -vf \"{vf_filter}\" -c:v libx264 -crf 22 -preset ultrafast -pix_fmt yuv420p -c:a aac -ac 2 -b:a 128k '{final_short}'"
            subprocess.run(ffmpeg_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            count += 1

        create_web_player(shorts_dir, len(moments))
        return True
    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        return False


def get_setup_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Shorts Setup</title>
<style>
body { background-color: #0f0f12; color: white; font-family: 'system-ui', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
.setup-box { background: #18181c; padding: 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 400px; text-align: center; }
h2 { color: #00ff00; margin-bottom: 20px; }
label { display: block; text-align: left; margin: 10px 0 5px; color: #aaa; font-size: 14px; }
input, select { width: 100%; padding: 12px; border-radius: 8px; border: none; background: #282830; color: white; margin-bottom: 15px; box-sizing: border-box; }
.btn-submit { background: linear-gradient(135deg, #00ffcc, #00ff00); color: #000; font-weight: bold; border: none; padding: 14px; border-radius: 8px; width: 100%; cursor: pointer; font-size: 16px; text-transform: uppercase; margin-top: 10px; }
#loader { display: none; color: #00ffcc; margin-top: 15px; font-weight: bold; }
</style>
</head>
<body>
<div class="setup-box">
<h2>🎬 Smart Shorts Config</h2>
<div id="formContainer">
<label>🔗 YouTube Video URL:</label>
<input type="text" id="url" placeholder="https://www.youtube.com/watch?v=...">

<label>🔑 Groq API Key:</label>
<input type="password" id="apiKey" placeholder="gsk_...">

<label>⏱️ Duration per clip (seconds):</label>
<input type="number" id="duration" value="30">

<label>🎬 Max Clips to Generate:</label>
<input type="number" id="maxClips" value="3">

<button class="btn-submit" onclick="startProcessing()">Generate Shorts</button>
</div>
<div id="loader">⏳ AI is finding highlights & baking videos... Please wait! (Check terminal for live logs)</div>
</div>

<script>
async function startProcessing() {
  const url = document.getElementById('url').value;
  const apiKey = document.getElementById('apiKey').value;
  const duration = document.getElementById('duration').value;
  const maxClips = document.getElementById('maxClips').value;

  if(!url || !apiKey) { alert("Please fill URL and Groq Key!"); return; }

  document.getElementById('formContainer').style.display = 'none';
  document.getElementById('loader').style.display = 'block';

  try {
    const response = await fetch('/process', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ url, apiKey, duration, maxClips })
    });
    const data = await response.json();
    if(data.status === 'success') {
      window.location.reload();
    } else {
      alert("Error: " + data.message);
      window.location.reload();
    }
  } catch(e) {
    alert("Processing failed. Make sure server terminal is running.");
    window.location.reload();
  }
}
</script>
</body>
</html>"""


def create_web_player(directory, max_clips):
    clip_options = "".join([f'<option value="{i}">Clip {i}</option>' for i in range(1, max_clips + 1)])

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Shorts Live Customizer</title>
<style>
body { background-color: #0f0f12; color: white; font-family: 'system-ui', sans-serif; text-align: center; padding: 15px; }
.container { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 5px; }
.video-wrapper { position: relative; width: 350px; height: 620px; border-radius: 16px; overflow: hidden; box-shadow: 0 15px 40px rgba(0,0,0,0.8); background: #000; }
video { width: 100%; height: 100%; object-fit: cover; }
.caption-overlay { position: absolute; bottom: 30%; width: 90%; left: 5%; text-align: center; pointer-events: none; word-wrap: break-word; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; }
.caption-word { display: inline-block; margin: 2px 6px; transition: all 0.1s ease; border-radius: 4px; padding: 2px 6px; }
.style-tiktok-classic .caption-word { font-weight: 900; color: #fff; text-shadow: 3px 3px 0 #000; text-transform: uppercase; }
.style-tiktok-classic .caption-word.active { color: var(--text-color, #00ff00); background: var(--bg-color, transparent); transform: scale(1.1); }
.style-yt-gold .caption-word { font-weight: 800; color: #fff; text-shadow: 2px 2px 4px rgba(0,0,0,0.9); font-family: 'Impact'; }
.style-yt-gold .caption-word.active { color: var(--text-color, #ffcc00); background: var(--bg-color, transparent); }
.style-one-word .caption-word { font-weight: 900; color: transparent; display: none; font-family: 'Impact'; }
.style-one-word .caption-word.active { display: inline-block; color: var(--text-color, #fff); background: var(--bg-color, transparent); text-shadow: 4px 4px 0px #ff0055; }
.style-hormozi .caption-word { font-weight: 900; color: #fff; text-shadow: 3px 3px 0px #000; font-family: 'Arial Black'; text-transform: uppercase; }
.style-hormozi .caption-word.active { color: var(--text-color, #ffea00); transform: scale(1.15) rotate(-3deg); background: var(--bg-color, #000); }
.style-cyber .caption-word { font-weight: 700; color: #333; text-shadow: 0 0 5px #00ffff; }
.style-cyber .caption-word.active { color: var(--text-color, #00ffff); background: var(--bg-color, transparent); text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff; }
.style-mrbeast .caption-word { font-weight: 900; color: #ffffff; text-shadow: 3px 3px 0px #000; }
.style-mrbeast .caption-word.active { color: var(--text-color, #00e5ff); background: var(--bg-color, transparent); transform: scale(1.25); }
.style-anime .caption-word { font-weight: 800; color: #e5e5e5; font-style: italic; }
.style-anime .caption-word.active { color: var(--text-color, #ff3333); background: var(--bg-color, transparent); transform: skewX(-10deg) scale(1.2); text-shadow: 2px 2px 0px #fff; }
.style-insta .caption-word { font-weight: 400; color: rgba(255,255,255,0.7); letter-spacing: 1px; }
.style-insta .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, transparent); border-bottom: 2px solid #fff; }
.style-ghost .caption-word { font-weight: 600; color: rgba(255,255,255,0.3); }
.style-ghost .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, transparent); text-shadow: 0 0 15px #fff; }
.style-comic .caption-word { font-weight: 900; color: #fff; font-family: 'Impact'; -webkit-text-stroke: 1px black; }
.style-comic .caption-word.active { color: var(--text-color, #ffff00); background: var(--bg-color, transparent); transform: scale(1.3) rotate(4deg); }
.style-arcade .caption-word { font-weight: bold; color: #ff00ff; font-family: 'Courier New'; }
.style-arcade .caption-word.active { color: var(--text-color, #00ffff); background: var(--bg-color, #222); }
.style-minimal .caption-word { font-weight: 500; color: #888; }
.style-minimal .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, transparent); transform: scale(1.05); }
.style-voltage .caption-word { font-weight: 900; color: #fff; text-shadow: 2px 2px 0px #990000; }
.style-voltage .caption-word.active { color: var(--text-color, #ff1100); background: var(--bg-color, transparent); animation: shake 0.1s infinite; }
.style-candy .caption-word { font-weight: bold; color: #fff; }
.style-candy .caption-word.active { color: var(--text-color, #ff77aa); background: var(--bg-color, transparent); transform: scale(1.1); }
.style-ice .caption-word { font-weight: 800; color: #b2f2ff; }
.style-ice .caption-word.active { color: var(--text-color, #00d2ff); background: var(--bg-color, transparent); text-shadow: 0 0 8px #fff; }
.style-ninja .caption-word { font-weight: 700; color: #444; }
.style-ninja .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, rgba(255,0,0,0.8)); }
.style-terminal .caption-word { font-family: monospace; color: #33ff33; opacity: 0.4; }
.style-terminal .caption-word.active { opacity: 1; color: var(--text-color, #33ff33); background: var(--bg-color, transparent); text-shadow: 0 0 5px #33ff33; }
.style-fire .caption-word { font-weight: 900; color: #eee; }
.style-fire .caption-word.active { color: var(--text-color, #ff9900); background: var(--bg-color, transparent); text-shadow: 0 0 10px #ff3300; }
.style-emerald .caption-word { font-weight: bold; color: #a1ffd0; }
.style-emerald .caption-word.active { color: var(--text-color, #00ff88); background: var(--bg-color, transparent); transform: scale(1.1); }
.style-impact-sub .caption-word { font-weight: 900; font-family: 'Impact'; color: #fff; }
.style-impact-sub .caption-word.active { color: var(--text-color, #00ffcc); background: var(--bg-color, transparent); }
.style-vip .caption-word { font-weight: bold; color: #ccc; }
.style-vip .caption-word.active { color: var(--text-color, #d4af37); background: var(--bg-color, rgba(0,0,0,0.5)); border: 1px solid #d4af37; }
.style-bounce .caption-word.active { animation: bounceJump 0.2s ease-out forwards; color: var(--text-color, #ffff00); background: var(--bg-color, transparent); font-weight: 900; }
.style-glitch .caption-word.active { color: var(--text-color, #ff00ff); background: var(--bg-color, transparent); text-shadow: 2px -2px #00ffff; font-weight: 900; }
.style-pastel .caption-word { color: #e0b0ff; }
.style-pastel .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, #b19cd9); }
.style-graffiti .caption-word { font-family: 'Impact'; }
.style-graffiti .caption-word.active { color: var(--text-color, #ffea00); background: var(--bg-color, transparent); transform: scale(1.2) rotate(3deg); }
.style-border-box .caption-word { padding: 4px; }
.style-border-box .caption-word.active { background: var(--bg-color, #fff); color: var(--text-color, #000); font-weight: bold; }
.style-flash .caption-word { color: #666; }
.style-flash .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, transparent); animation: blink 0.3s infinite; }
.style-runner .caption-word { font-weight: 800; transform: skewX(-15deg); }
.style-runner .caption-word.active { color: var(--text-color, #ffff00); background: var(--bg-color, #ff0000); }
.style-outline .caption-word { font-weight: 900; color: #fff; -webkit-text-stroke: 2px #000; }
.style-outline .caption-word.active { color: var(--text-color, #00ff00); background: var(--bg-color, transparent); }
.style-mafia .caption-word { font-weight: 900; text-transform: uppercase; color: #555; }
.style-mafia .caption-word.active { color: var(--text-color, #fff); background: var(--bg-color, transparent); text-shadow: 0 4px 10px rgba(255,255,255,0.5); }
@keyframes bounceJump { 0% { transform: translateY(0); } 50% { transform: translateY(-10px); } 100% { transform: translateY(0); } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
@keyframes shake { 0% { transform: translate(1px, 1px); } 100% { transform: translate(-1px, -1px); } }
.controls { margin-top: 15px; background: #18181c; padding: 15px; border-radius: 12px; width: 330px; box-sizing: border-box; }
label { display: block; margin: 8px 0 4px; font-size: 13px; text-align: left; color: #aaa; }
select, input { width: 100%; padding: 10px; border-radius: 6px; border: none; background: #282830; color: white; margin-bottom: 8px; font-size: 14px; }
.btn-export { background: linear-gradient(135deg, #00ffcc, #00ff00); color: #000; font-weight: bold; border: none; padding: 12px; border-radius: 8px; width: 100%; cursor: pointer; font-size: 16px; margin-top: 5px; text-transform: uppercase; }
.btn-reset { background: #3a3a44; color: #fff; font-weight: normal; border: none; padding: 6px; border-radius: 4px; width: 100%; cursor: pointer; font-size: 12px; margin-top: 10px; }
</style>
</head>
<body>
<div class="container">
<div class="video-wrapper">
<video id="shortPlayer" controls autoplay loop>
<source id="videoSource" src="viral_short_1.mp4" type="video/mp4">
</video>
<div id="captionBox" class="caption-overlay style-tiktok-classic"></div>
</div>

<div class="controls">
<h3 style="margin:0 0 10px 0; color:#00ff00;">🎯 Smart Shorts Mega Dashboard</h3>
<label style="color:#00ffcc; font-weight:bold;">🎬 Choose Active Clip:</label>
<select id="clipSelector">CLIP_OPTIONS</select>
<label>⚡ Select Live Template:</label>
<select id="styleSelector">
<option value="style-tiktok-classic">1. TikTok Classic Style 🟢</option>
<option value="style-yt-gold">2. YouTube Shorts Gold 🟡</option>
<option value="style-one-word">3. Word-by-Word Pop (1 Word) ⚡</option>
<option value="style-hormozi">4. Alex Hormozi Style 🔥</option>
<option value="style-cyber">5. Cyberpunk Neon Glow 🩵</option>
<option value="style-mrbeast">6. MrBeast Aggressive Pop 💥</option>
<option value="style-anime">7. Anime Fast Skew 🔴</option>
<option value="style-insta">8. Instagram Luxury Aesthetic ✨</option>
<option value="style-ghost">9. Glowing Ghost Aura 👻</option>
<option value="style-comic">10. Comic Book Zoom 📚</option>
<option value="style-arcade">11. Retro Arcade 8-Bit 👾</option>
<option value="style-minimal">12. Minimalist Smooth Clean ⚪</option>
<option value="style-voltage">13. High Voltage Red Shake 🚨</option>
<option value="style-candy">14. Sweet Candy Pink 🌸</option>
<option value="style-ice">15. Ice Cold Diamond Blue ❄️</option>
<option value="style-ninja">16. Shadow Ninja Dark Box 🥷</option>
<option value="style-terminal">17. Typewriter Hacker Green 💻</option>
<option value="style-fire">18. Fire Flame Burning 🔥</option>
<option value="style-emerald">19. Deep Sea Emerald 🍏</option>
<option value="style-impact-sub">20. Bold Heavy Impact 🔨</option>
<option value="style-vip">21. VIP Rich Gold Border 👑</option>
<option value="style-bounce">22. Bounce Pop Jump 🦘</option>
<option value="style-glitch">23. Glitch Matrix Cyber 🧬</option>
<option value="style-pastel">24. Soft Pastel Purple 🍇</option>
<option value="style-graffiti">25. Graffiti Street Wild 🎨</option>
<option value="style-border-box">26. Modern Corporate Invert 🔳</option>
<option value="style-flash">27. Flash Light Blinker 🔦</option>
<option value="style-runner">28. Speed Runner Red 🚩</option>
<option value="style-outline">29. Deep Heavy Black Outline 🖤</option>
<option value="style-mafia">30. Billionaire Mafia Style 💎</option>
</select>
<label>🌈 Word Highlight Color:</label>
<select id="textColor">
<option value="#00ff00" selected>TikTok Green 🟢</option>
<option value="#ffff00">Classic Yellow 🟡</option>
<option value="#00ffff">Neon Cyan 🩵</option>
<option value="#ffffff">Pure White ⚪</option>
<option value="#ff3333">Danger Red 🔴</option>
<option value="#d4af37">VIP Gold 👑</option>
<option value="#ff007f">Hot Pink 🌸</option>
</select>
<label>🔳 Caption Background Box:</label>
<select id="bgColor">
<option value="none" selected>No Background Box</option>
<option value="rgba(0,0,0,0.6)">Semi-Transparent Black</option>
<option value="#000000">Solid Black Box</option>
<option value="#ff3333">Solid Red Box</option>
<option value="#0000ff">Solid Blue Box</option>
<option value="#ffffff">Solid White Box</option>
</select>
<label>↕️ Position (Height %):</label>
<input type="range" id="captionLine" min="10" max="80" value="30" step="1">
<label id="fontSizeLabel">📐 Font Size: 26px</label>
<input type="range" id="fontSizeSlider" min="16" max="60" value="26" step="1">
<button class="btn-export" id="btnExport">🎬 Export Current Clip</button>
<button class="btn-reset" onclick="localStorage.clear(); window.location.href='/';">🔄 Process New Link</button>
<div id="statusOutput" style="margin-top:10px; font-size:13px; color:#00ffcc;"></div>
</div>
</div>

<script>
const player = document.getElementById('shortPlayer');
const videoSource = document.getElementById('videoSource');
const captionBox = document.getElementById('captionBox');
const styleSelector = document.getElementById('styleSelector');
const fontSizeSlider = document.getElementById('fontSizeSlider');
const fontSizeLabel = document.getElementById('fontSizeLabel');
const textColorSelector = document.getElementById('textColor');
const bgColorSelector = document.getElementById('bgColor');
const captionLine = document.getElementById('captionLine');
const clipSelector = document.getElementById('clipSelector');
const btnExport = document.getElementById('btnExport');
const statusOutput = document.getElementById('statusOutput');
let captionsData = [];

async function loadCaptions(id) {
  try {
    const response = await fetch(`viral_short_${id}.json`);
    captionsData = await response.json();
  } catch (e) { console.error(e); }
}

clipSelector.addEventListener('change', async (e) => {
  const id = e.target.value;
  videoSource.src = `viral_short_${id}.mp4`;
  player.load(); player.play();
  statusOutput.innerText = "";
  await loadCaptions(id);
});

player.addEventListener('timeupdate', () => {
  const currentTime = player.currentTime;
  let currentLine = captionsData.find(c => currentTime >= c.start && currentTime <= c.end);
  if (currentLine) {
    let html = "";
    currentLine.words.forEach(w => {
      const isActive = currentTime >= w.start && currentTime <= w.end;
      html += `<span class="caption-word ${isActive ? 'active' : ''}">${w.text}</span>`;
    });
    captionBox.innerHTML = html;
  } else {
    captionBox.innerHTML = "";
  }
});

styleSelector.addEventListener('change', (e) => { captionBox.className = "caption-overlay " + e.target.value; });
captionLine.addEventListener('input', (e) => { captionBox.style.bottom = e.target.value + '%'; });

fontSizeSlider.addEventListener('input', (e) => {
  captionBox.style.fontSize = e.target.value + 'px';
  fontSizeLabel.innerText = `📐 Font Size: ${e.target.value}px`;
});

textColorSelector.addEventListener('change', (e) => { document.documentElement.style.setProperty('--text-color', e.target.value); });
bgColorSelector.addEventListener('change', (e) => { document.documentElement.style.setProperty('--bg-color', e.target.value); });

btnExport.addEventListener('click', async () => {
  statusOutput.innerText = `⏳ Exporting Clip ${clipSelector.value} with Custom Colors...`;
  try {
    const response = await fetch('/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clipId: clipSelector.value,
        style: styleSelector.value,
        position: captionLine.value,
        textColor: textColorSelector.value,
        bgColor: bgColorSelector.value,
        fontSize: fontSizeSlider.value
      })
    });
    const resData = await response.json();
    if(resData.status === "success") {
      statusOutput.innerHTML = `✅ Baked with Custom Colors!<br><a href="${resData.video}" download style="color:#fff; font-weight:bold; text-decoration:underline;">📥 Download Video</a>`;
    }
  } catch(e) { statusOutput.innerText = "❌ Export failed."; }
});

window.addEventListener('DOMContentLoaded', () => {
  loadCaptions(1);
  captionBox.style.fontSize = fontSizeSlider.value + 'px';
  document.documentElement.style.setProperty('--text-color', textColorSelector.value);
  document.documentElement.style.setProperty('--bg-color', bgColorSelector.value);
});
</script>
</body>
</html>"""
    final_html = html_content.replace("CLIP_OPTIONS", clip_options)
    with open(os.path.join(directory, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)


def start_server(port=8080):
    global shorts_dir
    os.makedirs(shorts_dir, exist_ok=True)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), SmartShortsHandler) as httpd:
        print("\n" + "="*50)
        print(f"🌍 WEB SERVER ONLINE!\n👉 Open browser at: http://localhost:{port}")
        print("="*50 + "\n")
        httpd.serve_forever()


def main():
    initialize_app_assets()
    start_server(port=8080)


if __name__ == '__main__':
    main()
