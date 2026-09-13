# app.py
import gradio as gr
from companion import ChatCompanion
import os
import base64

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def file_to_base64(path, mime="video/webm"):
    """Read a file and return a data URI string."""
    if not os.path.exists(path):
        print(f"[WARN] Missing asset: {path}")
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

    # Convert the map into a JS object literal
    import json
    video_map_js = json.dumps(video_map)

    def user_submit(message, history):
        if not message.strip():
            return "", history, ""
        reply, action = companion.chat(message)
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        return "", history, action

    def clear_chat():
        companion.short_mem.messages = [
            {"role": "system", "content": companion.system_prompt}
        ]
        companion.exchange_count = 0
        return [], "idle"

    # ---------- JS to play animations from preloaded map ----------
    js_play_action = f"""
    (action) => {{
        const videoMap = {video_map_js};
        const avatar = document.querySelector('#Virgo-avatar video');
        if (!avatar) return;

        const url = videoMap[action] || videoMap['idle'];
        if (!url) return;

        // Clear any previous listeners to avoid duplicates
        if (window._VirgoEndHandler) {{
            avatar.removeEventListener('ended', window._VirgoEndHandler);
        }}

        // If it's the idle video, keep it looping forever
        if (action === 'idle') {{
            avatar.loop = true;
            avatar.src = url;
            avatar.play().catch(e => console.warn('play() failed:', e));
            return;
        }}

        // Playing an action video – disable loop so 'ended' fires
        avatar.loop = false;
        avatar.src = url;
        avatar.play().catch(e => console.warn('play() failed:', e));

        // When the action video finishes, return to idle
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

    with gr.Blocks(
        title="Virgo – AI Companion",
        head="""
        <style>
        /* Remove Gradio's default padding around the column */
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
            min-height: 620px;      /* matches chatbot height + input area */
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
            object-fit: cover;       /* fills the frame, may crop edges */
            /* object-fit: contain;  /* use this instead to fit fully without cropping */
        }

        /* Overlay name + status at the bottom of the frame */
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
        """,
    ) as demo:
        gr.Markdown("#  Virgo")

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
                with gr.Row():
                    clear_btn = gr.Button("🧹 Clear Chat", size="sm")
                    gr.Markdown("_Long‑term memories are preserved._")

            with gr.Column(scale=1, min_width=250):
                # Embed idle video inline as base64 (via the first available URI)
                idle_uri = video_map.get("idle", "")
                gr.HTML(f"""
                    <div id="Virgo-panel">
                        <div id="Virgo-avatar">
                            <video autoplay loop muted playsinline
                                   src="{idle_uri}"></video>
                        </div>
                        <div id="Virgo-name">Virgo</div>
                        <div id="Virgo-status">● online</div>
                    </div>
                """)

        action_box = gr.Textbox(visible=False, value="idle")

        msg_box.submit(
            user_submit,
            inputs=[msg_box, chatbot],
            outputs=[msg_box, chatbot, action_box],
        ).then(fn=None, inputs=action_box, js=js_play_action)

        send_btn.click(
            user_submit,
            inputs=[msg_box, chatbot],
            outputs=[msg_box, chatbot, action_box],
        ).then(fn=None, inputs=action_box, js=js_play_action)

        clear_btn.click(clear_chat, outputs=[chatbot, action_box])

    return demo


if __name__ == "__main__":
    companion = ChatCompanion()
    app = create_app(companion)
    app.launch(
        theme=gr.themes.Soft(primary_hue="purple", secondary_hue="pink"),
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
        # allowed_paths no longer needed
    )
'''
# app.py
import gradio as gr
from companion import ChatCompanion
import os

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def create_app(companion: ChatCompanion):
    """Build and return a Gradio Blocks app."""

    def user_submit(message, history):
        """Called when user sends a message. history is ignored (companion has its own)."""
        if not message.strip():
            return "", history, ""
        reply, action = companion.chat(message)
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        return "", history, action  # action goes to a hidden textbox

    def clear_chat():
        """Reset short‑term memory but keep long‑term facts."""
        companion.short_mem.messages = [
            {"role": "system", "content": companion.system_prompt}
        ]
        companion.exchange_count = 0
        return [], "idle"


    # ---------- Custom JS to play animations ----------
    js_play_action = """
    (action) => {
        const avatar = document.querySelector('#Virgo-avatar video, #Virgo-avatar img');
        if (!avatar) return;
        const ext = avatar.tagName === 'VIDEO' ? '.webm' : '.gif';
        const idle = avatar.dataset.idle;
        // Set the new source
        if (avatar.tagName === 'VIDEO') {
            avatar.src = `file=assets/Virgo_${action}.webm`;
            avatar.play();
        } else {
            avatar.src = `file=assets/Virgo_${action}.gif`;
        }
        // Return to idle after 3 seconds
        clearTimeout(window._VirgoTimer);
        window._VirgoTimer = setTimeout(() => {
            if (avatar.tagName === 'VIDEO') {
                avatar.src = `file=assets/Virgo_idle.webm`;
                avatar.play();
            } else {
                avatar.src = `file=assets/Virgo_idle.gif`;
            }
        }, 3000);
    }
    """

    with gr.Blocks(
        title="Virgo – AI Companion",
        head=f"""
        <style>
            #Virgo-panel {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px;
                background: linear-gradient(180deg, #1a1a2e, #0f0f1e);
                border-radius: 20px;
                height: 100%;
            }}
            #Virgo-avatar {{
                width: 220px;
                height: 220px;
                border-radius: 50%;
                overflow: hidden;
                box-shadow: 0 0 40px rgba(192, 132, 252, 0.5);
                border: 3px solid #c084fc;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #000;
            }}
            #Virgo-avatar video, #Virgo-avatar img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}
            #Virgo-name {{
                color: #c084fc;
                font-size: 1.4em;
                font-weight: bold;
                margin-top: 16px;
                letter-spacing: 1px;
            }}
            #Virgo-status {{
                color: #888;
                font-size: 0.9em;
                margin-top: 4px;
            }}
        </style>
        """,
    ) as demo:
        gr.Markdown("#  Virgo")

        with gr.Row():
            # ----- LEFT: Chat -----
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Virgo",
                    height=550,
                    #show_copy_button=True,
                )
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="Say something to Virgo...",
                        show_label=False,
                        scale=9,
                        autofocus=True,
                        container=False,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                with gr.Row():
                    clear_btn = gr.Button("🧹 Clear Chat", size="sm")
                    gr.Markdown("_Long‑term memories are preserved._")

            # ----- RIGHT: Animated Avatar -----
            with gr.Column(scale=1, min_width=250):
                gr.HTML(f"""
                    <div id="Virgo-panel">
                        <div id="Virgo-avatar">
                            <video src="file={ASSETS}/Virgo_idle.webm"
                                   autoplay loop muted playsinline
                                   data-idle="idle"></video>
                        </div>
                        <div id="Virgo-name">Virgo</div>
                        <div id="Virgo-status">● online</div>
                    </div>
                """)
#---------------------------------------------------------------


#-------------------------------------------------------------
        # Hidden textbox to carry the action from Python to JS
        action_box = gr.Textbox(visible=False, value="idle")

        # Wire up events
        msg_box.submit(
            user_submit, inputs=[msg_box, chatbot], outputs=[msg_box, chatbot, action_box],
        ).then(
            fn=None,
            inputs=action_box,
            js=js_play_action,
        )
        send_btn.click(
            user_submit, inputs=[msg_box, chatbot], outputs=[msg_box, chatbot, action_box]
        )
        clear_btn.click(clear_chat, outputs=[chatbot, action_box])

    return demo


if __name__ == "__main__":
    companion = ChatCompanion()
    app = create_app(companion)
    # 3. FIX: Pass `theme` to the launch method
    app.launch(
        theme=gr.themes.Soft(primary_hue="purple", secondary_hue="pink"),
        server_name="127.0.0.1",
        server_port=7860,
        share=False,          # set True for a public gradio.live link
        inbrowser=True,       # auto‑open in browser
        allowed_paths=[ASSETS],
    )
    '''