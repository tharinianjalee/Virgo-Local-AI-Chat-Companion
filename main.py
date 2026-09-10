# main.py
import sys
from companion import ChatCompanion


def run_cli():
    companion = ChatCompanion()
    print("Nova: Hello! I'm your companion. Type 'exit' to quit.")
    while True:
        user = input("You: ")
        if user.lower() == "exit":
            break
        reply = companion.chat(user)
        print(f"Nova: {reply}")


def run_gradio():
    import gradio as gr

    companion = ChatCompanion()

    def respond(message, history):
        return companion.chat(message)

    iface = gr.ChatInterface(fn=respond, title="Nova Companion")
    iface.launch()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gradio":
        run_gradio()
    else:
        run_cli()