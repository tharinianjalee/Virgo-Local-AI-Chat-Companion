# Copyright 2025 Baduge Tharini Anjalee Fernando
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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