# app.py
import gradio as gr
from companion import ChatCompanion
import os
import base64
import json

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


CSS = """
<style>
    .avatar-column {
        padding: 0 !important;
        overflow: hidden;
        border-radius: 20px;
    }
    #Virgo-panel {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        padding: 0;
        background: linear-gradient(180deg, #1a1a2e, #0f0f1e);
        border-radius: 20px;
        height: 100%;
        min-height: 620px;
        width: 100%;
        overflow: hidden;
        position: relative;
    }
    #Virgo-avatar {
        width: 100%;
        height: 100%;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 0 40px rgba(192, 132, 252, 0.4);
        border: 3px solid #c084fc;
        background: #000;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 1;
    }
    #Virgo-avatar video {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    #Virgo-info {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 16px;
        background: linear-gradient(to top, rgba(0,0,0,0.85), transparent);
        text-align: center;
        pointer-events: none;
    }
    #Virgo-name {
        color: #c084fc;
        font-size: 1.6em;
        font-weight: bold;
        letter-spacing: 1px;
    }
    #Virgo-status {
        color: #ccc;
        font-size: 0.9em;
        margin-top: 4px;
    }
</style>
"""


def file_to_base64(path, mime="video/webm"):
    """Read a file and return a data URI string."""
    if not os.path.exists(path):
        print(f"[WARN] Missing asset: {path}")
        return ""
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{encoded}"

def audio_to_base64_data_uri(path, mime="audio/wav"):
    """Read a WAV file and return a data URI."""
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{encoded}"

def create_app(companion: ChatCompanion):
    """Build and return a Gradio Blocks app."""

    # ---------- Preload all action videos as base64 ----------
    ACTIONS = ["idle", "smile", "laugh", "hug", "thumbsup", "embarrassed", "neutral"]
    video_map = {}
    for action in ACTIONS:
        path = os.path.join(ASSETS, f"Virgo_{action}_new.webm")
        uri = file_to_base64(path, "video/webm")
        if uri:
            video_map[action] = uri
            print(f"[OK] Loaded Virgo_{action}.webm ({len(uri)//1024} KB)")
        else:
            print(f"[MISS] Virgo_{action}.webm not found – skipping")

    if "idle" not in video_map:
        print("[ERROR] Virgo_idle.webm is missing – avatar will not show.")

    video_map_js = json.dumps(video_map)

    _last_mic_path = {"value": None}

    def on_mic_stop(audio_path, history):
        if not audio_path:
            return "", history, "idle", ""

        # Skip if it's the exact same file as last time
        if audio_path == _last_mic_path["value"]:
            print(f"[DEBUG] Ignoring duplicate mic path: {audio_path}")
            return "", history, "idle", ""
        _last_mic_path["value"] = audio_path

        text = companion.transcribe(audio_path)
        if not text:
            return "", history, "idle", ""

        return user_submit(text, history)

    def user_submit(message, history):
        if not message.strip():
            return "", history, "", ""
        reply, action, audio_path = companion.chat(message)
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        # Convert WAV → base64 data URI (or empty string)
        audio_data_uri = ""
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            audio_data_uri = f"data:audio/wav;base64,{b64}"

        return "", history, action, audio_data_uri

    def clear_chat():
        companion.short_mem.messages = [
            {"role": "system", "content": companion.system_prompt}
        ]
        companion.exchange_count = 0
        return [], "idle", ""

    def on_mic_stop(audio_path, history):
        """Called when the user finishes recording."""
        if not audio_path:
            return "", history, "idle", ""

        # Transcribe
        text = companion.transcribe(audio_path)
        if not text:
            return "", history, "idle", ""

        # Reuse the normal submit flow
        return user_submit(text, history)

    js_play_action = f"""
    (action) => {{
        const videoMap = {video_map_js};
        const avatar = document.querySelector('#Virgo-avatar video');
        if (!avatar) return;

        const url = videoMap[action] || videoMap['idle'];
        if (!url) return;

        if (window._VirgoEndHandler) {{
            avatar.removeEventListener('ended', window._VirgoEndHandler);
        }}

        if (action === 'idle') {{
            avatar.loop = true;
            avatar.src = url;
            avatar.play().catch(e => console.warn('play() failed:', e));
            return;
        }}

        avatar.loop = false;
        avatar.src = url;
        avatar.play().catch(e => console.warn('play() failed:', e));

        window._VirgoEndHandler = () => {{
            const idleUrl = videoMap['idle'];
            if (idleUrl) {{
                avatar.loop = true;
                avatar.src = idleUrl;
                avatar.play().catch(e => console.warn('idle play() failed:', e));
            }}
        }};
        avatar.addEventListener('ended', window._VirgoEndHandler, {{ once: true }});
    }}
    """
    js_play_audio = """
    (audio_uri) => {
        if (!audio_uri) return;
        let el = document.getElementById('virgo-audio-player');
        if (!el) {
            el = document.createElement('audio');
            el.id = 'virgo-audio-player';
            el.style.display = 'none';
            document.body.appendChild(el);
        }
        el.src = audio_uri;
        el.volume = 1.0;
        el.play().catch(e => console.warn('audio autoplay blocked:', e));
    }
    """
    with gr.Blocks(title="Virgo – AI Companion") as demo:
        gr.Markdown("# 🌟 Virgo")

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="Virgo", height=550)
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="Say something to Virgo...",
                        show_label=False,
                        scale=9,
                        autofocus=True,
                        container=False,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                    mic_btn = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        label="",
                        show_label=False,
                        container=False,
                        scale=1,
                    )
                with gr.Row():
                    clear_btn = gr.Button("🧹 Clear Chat", size="sm")
                    gr.Markdown("_Long‑term memories are preserved._")

            with gr.Column(scale=1, min_width=300, elem_classes="avatar-column"):
                idle_uri = video_map.get("idle", "")
                gr.HTML(f"""
                    <div id="Virgo-panel">
                        <div id="Virgo-avatar">
                            <video autoplay loop muted playsinline
                                   src="{idle_uri}"></video>
                        </div>
                        <div id="Virgo-info">
                            <div id="Virgo-name">Virgo</div>
                            <div id="Virgo-status">● online</div>
                        </div>
                    </div>
                """)

        action_box = gr.Textbox(visible=False, value="idle")

        #audio_out = gr.Audio(label="",autoplay=True,visible=False,show_label=False,waveform_options={"show_recording_waveform": False},)
        #audio_html = gr.HTML("", visible=False)
        audio_box = gr.Textbox(visible=False, value="")

        msg_box.submit(
            user_submit,
            inputs=[msg_box, chatbot],
            outputs=[msg_box, chatbot, action_box, audio_box],
        ).then(fn=None, inputs=action_box, js=js_play_action).then(fn=None, inputs=audio_box, js=js_play_audio)

        send_btn.click(
            user_submit,
            inputs=[msg_box, chatbot],
            outputs=[msg_box, chatbot, action_box, audio_box],
        ).then(fn=None, inputs=action_box, js=js_play_action).then(fn=None, inputs=audio_box, js=js_play_audio)

        mic_btn.stop_recording(
            on_mic_stop,
                inputs=[mic_btn, chatbot],
                outputs=[msg_box, chatbot, action_box, audio_box],
        ).then(fn=None, inputs=action_box, js=js_play_action).then(fn=None, inputs=audio_box, js=js_play_audio)

        clear_btn.click(clear_chat, outputs=[chatbot, action_box, audio_box])

    return demo


if __name__ == "__main__":
    companion = ChatCompanion()
    app = create_app(companion)
    app.launch(
        theme=gr.themes.Soft(primary_hue="purple", secondary_hue="pink"),
        head=CSS,
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
    )