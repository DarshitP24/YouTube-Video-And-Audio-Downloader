from flask import Flask, render_template, request, send_file, after_this_request, jsonify
import yt_dlp
import os, re, tempfile

app = Flask(__name__)
progress_data = {"percent": 0}

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def progress_hook(d):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0.0%').replace('%', '').strip()
        try:
            progress_data["percent"] = int(float(p))
        except:
            pass
    elif d['status'] == 'finished':
        progress_data["percent"] = 100

@app.route("/progress")
def progress():
    return jsonify(progress_data)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        quality = request.form.get("quality", "720")
        mode = request.form["mode"]
        progress_data["percent"] = 0

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = sanitize_filename(info.get('title', 'media'))

            temp_dir = tempfile.mkdtemp()

            if mode == "audio":
                filename = f"{title}.mp3"
                filepath = os.path.join(temp_dir, filename)
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(temp_dir, f"{title}.%(ext)s"),
                    "progress_hooks": [progress_hook],
                    "quiet": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                }
            else:
                filename = f"{title}.mp4"
                filepath = os.path.join(temp_dir, filename)
                ydl_opts = {
                    "format": f"bestvideo[ext=mp4][height<={quality}]+bestaudio[ext=m4a]/best[ext=mp4]",
                    "outtmpl": filepath,
                    "merge_output_format": "mp4",
                    "progress_hooks": [progress_hook],
                    "quiet": True,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            @after_this_request
            def cleanup(response):
                try:
                    for f in os.listdir(temp_dir):
                        os.remove(os.path.join(temp_dir, f))
                    os.rmdir(temp_dir)
                except:
                    pass
                return response

            return send_file(filepath, as_attachment=True, download_name=filename)

        except Exception as e:
            return f"Error: {str(e)}"

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, threaded=True)