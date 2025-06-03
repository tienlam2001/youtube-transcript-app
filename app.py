from flask import Flask, request, render_template_string, make_response, redirect
from youtube_transcript_api import YouTubeTranscriptApi
import re
import html
from fpdf import FPDF

app = Flask(__name__)

def extract_video_id(url):
    match = re.search(
        r"(?:v=|\/|be\/|embed\/)([0-9A-Za-z_-]{11})",
        url
    )
    return match.group(1) if match else None

@app.route('/', methods=['GET'])
def index():
    error_message = request.args.get('error', '')
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Transcript Extractor</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 40px;
                background: #1e1e2f;
                color: #f1f1f1;
            }}
            h1 {{
                color: #00bcd4;
            }}
            input[type=text] {{
                width: 80%;
                padding: 12px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                background: #2e2e3e;
                color: #fff;
                transition: background 0.3s ease;
            }}
            button {{
                padding: 12px 24px;
                font-size: 16px;
                margin-top: 15px;
                background: #00bcd4;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: background 0.3s ease;
            }}
            button:hover {{
                background: #0097a7;
            }}
            .transcript {{
                white-space: pre-wrap;
                background: #2e2e3e;
                padding: 20px;
                border-radius: 5px;
                margin-top: 30px;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
                color: #fff;
            }}
        </style>
    </head>
    <body>
        <h1>YouTube Transcript Extractor</h1>
        {'<p style="color:#ff6b6b;">' + error_message + '</p>' if error_message else ''}
        <form action="/get-transcript" method="post">
            <div style="margin-top:20px;">
                <input type="text" name="youtube_url" placeholder="https://www.youtube.com/watch?v=..." required>
            </div>
            <div style="margin-top:20px;">
                <button type="submit">Get Transcript</button>
            </div>
        </form>
    </body>
    </html>
    '''

@app.route('/get-transcript', methods=['POST'])
def get_transcript():
    url = request.form.get('youtube_url')
    video_id = extract_video_id(url)
    if not video_id:
        return redirect('/?error=Invalid+YouTube+URL')

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        import requests
        try:
            resp = requests.get(
                f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json',
                timeout=5
            )
            resp.raise_for_status()
            video_title = resp.json().get('title', 'transcript')
        except Exception:
            video_title = 'transcript'

        video_title = re.sub(r'[\\/*?:"<>|]', "_", video_title)
        text = "\n".join([entry['text'] for entry in transcript])
        escaped_text = html.escape(text)
        return render_template_string(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Transcript</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 40px;
                    background: #1e1e2f;
                    color: #f1f1f1;
                }}
                .transcript {{
                    white-space: pre-wrap;
                    background: #2e2e3e;
                    padding: 20px;
                    border-radius: 5px;
                    margin-top: 30px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.3);
                    color: #fff;
                }}
                button {{
                    padding: 12px 24px;
                    font-size: 16px;
                    margin-top: 15px;
                    background: #00bcd4;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: background 0.3s ease;
                }}
                button:hover {{
                    background: #0097a7;
                }}
                div.button-group {{
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>Transcript</h1>
            <div class="button-group">
                <div style="margin-top:20px;">
                    <button onclick="downloadPDF()">Download as PDF</button>
                </div>
                <div style="margin-top:20px;">
                    <form action="/" method="get" style="display:inline;">
                        <button type="submit">Get Transcript for Another Video</button>
                    </form>
                </div>
            </div>
            <div class="transcript">{escaped_text}</div>
            <script>
            async function downloadPDF() {{
                const text = `{escaped_text}`.replace(/&#x27;/g, "'");
                const title = `{html.escape(video_title)}`;

                const response = await fetch("/download-pdf", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
                    body: new URLSearchParams({{ content: text, title: title }})
                }});

                const blob = await response.blob();

                if (typeof window.showSaveFilePicker === "function") {{
                    // Chrome/Edge with File System Access API
                    const fileHandle = await window.showSaveFilePicker({{
                        suggestedName: title + ".pdf",
                        types: [{{ description: "PDF File", accept: {{ "application/pdf": [".pdf"] }} }}]
                    }});
                    const writable = await fileHandle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                }} else {{
                    // Safari and fallback
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = title + ".pdf";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }}
            }}
            </script>
        </body>
        </html>
        ''')
    except Exception as e:
        return redirect(f"/?error={html.escape(str(e))}")

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    text = request.form.get('content')
    title = request.form.get('title', 'transcript')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={title}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)
