from flask import Flask, request, render_template_string, make_response
from youtube_transcript_api import YouTubeTranscriptApi
import re
import html
from fpdf import FPDF

app = Flask(__name__)

def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

@app.route('/', methods=['GET'])
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Transcript Extractor</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; }
            h1 { color: #333; }
            input[type=text] { width: 80%; padding: 10px; font-size: 16px; }
            button { padding: 10px 20px; font-size: 16px; margin-top: 10px; }
            .transcript { white-space: pre-wrap; background: #fff; padding: 20px; border-radius: 5px; margin-top: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <h1>YouTube Transcript Extractor</h1>
        <form action="/get-transcript" method="post">
            <input type="text" name="youtube_url" placeholder="https://www.youtube.com/watch?v=..." required>
            <br>
            <button type="submit">Get Transcript</button>
        </form>
    </body>
    </html>
    '''

@app.route('/get-transcript', methods=['POST'])
def get_transcript():
    url = request.form.get('youtube_url')
    video_id = extract_video_id(url)
    if not video_id:
        return '<h2>Error: Invalid YouTube URL</h2>', 400

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = "\n".join([entry['text'] for entry in transcript])
        escaped_text = html.escape(text)
        return render_template_string(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Transcript</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; }}
                .transcript {{ white-space: pre-wrap; background: #fff; padding: 20px; border-radius: 5px; margin-top: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                button {{ padding: 10px 20px; font-size: 16px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>Transcript</h1>
            <form action="/download-pdf" method="post">
                <input type="hidden" name="content" value="{escaped_text}">
                <button type="submit">Download as PDF</button>
            </form>
            <div class="transcript">{escaped_text}</div>
        </body>
        </html>
        ''')
    except Exception as e:
        return f'<h2>Error: {html.escape(str(e))}</h2>', 500

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    text = request.form.get('content')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=transcript.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)
