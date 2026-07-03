"""
Chat App example using INGUITIVE framework.

Demonstrates:
- Real-time chat interface with bot responses
- State management for chat history
- Form handling with trigger handlers

Features:
- User can type questions
- Bot responds with funny answers
- Chat history persists during the session

Run with: uvicorn examples.chat_app:app --reload
"""

import random
from pathlib import Path

from inguitive import Button, Div, Form, Icon, Input, State, Text, create_app, update_components

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent.parent / "templates")


# --- CSS ---
COLOR_BASE = "slate"
COLOR_100 = f"{COLOR_BASE}-100"
COLOR_200 = f"{COLOR_BASE}-200"
COLOR_300 = f"{COLOR_BASE}-300"
COLOR_400 = f"{COLOR_BASE}-400"
COLOR_900 = f"{COLOR_BASE}-900"
COLOR_BRAND_1 = "blue-700"
COLOR_BRAND_2 = "fuchsia-600"
COLOR_BRAND_2_LIGHT = "fuchsia-500"
BUTTON_SHAPE = "p-3 rounded-md font-semibold cursor-pointer shadow-lg active:shadow-none"
BUTTON_PRIMARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_BRAND_1} to-{COLOR_BRAND_2} text-{COLOR_100} hover:to-{COLOR_BRAND_2_LIGHT}"
BUTTON_SECONDARY = (
    f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_400} to-{COLOR_300} text-{COLOR_900} hover:to-{COLOR_200}"
)
PAGE = f"min-h-screen bg-{COLOR_900} flex justify-center items-end"
CARD = "max-w-2xl mx-auto p-6 space-y-6 bg-white rounded-xl shadow-md"
TEXT_CONTAINER = "w-full flex flex-grow p-6 rounded-lg bg-white justify-center items-center"


# --- Icons ---
ARROW_UP_ICON = f"""
<svg class="w-5 h-5 text-{COLOR_100}" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
  <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v13m0-13 4 4m-4-4-4 4"/>
</svg>
"""

USER_ICON = f"""
<svg class="w-5 h-5 text-{COLOR_100}" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
  <path stroke="currentColor" stroke-width="2" d="M7 17v1a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-1a3 3 0 0 0-3-3h-4a3 3 0 0 0-3 3Zm8-9a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
</svg>
"""

LIGHTBULB_ICON = f"""
<svg class="w-5 h-5 text-{COLOR_100}" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
  <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9a3 3 0 0 1 3-3m-2 15h4m0-3c0-4.1 4-4.9 4-9A6 6 0 1 0 6 9c0 4 4 5 4 9h4Z"/>
</svg>
"""


answers = [
    "I have no idea.",
    "Sorry, I don't know.",
    "Who knows, who knows...",
    "Great question! Can we talk about something else?",
    "I'm not sure. Maybe you should ask your neighbor.",
    "How am I supposed to know that?",
    "I always say, 'There are no stupid questions, only stupid answers.' But right now, I'm not so sure about that anymore...",
    "Please ask me again tomorrow.",
    "Could you repeat the question?",
    "I don't think there's anyone out there who can answer that.",
]

# State to store chat history as list of [speaker, message] pairs
chat_history_state = State([["bot", "Ask me anything!"]], "chat_history_state")


@app.trigger_handler
def generate_bot_response(form_data: dict):
    """Generate a bot response based on the user's message.

    Args:
        form_data: Dictionary containing form submission data with 'message' key

    Returns:
        str: HTMX update response for component listeners
    """
    user_message = form_data.get("message", "").strip()
    if not user_message:
        return ""

    chat_history = chat_history_state.get()
    chat_history.append(["user", user_message])
    if "?" in user_message:
        answer = random.choice(answers)
    else:
        answer = "I don't think that's a question... Could you ask me a question?"
    chat_history.append(["bot", answer])
    chat_history_state.set(chat_history)
    return update_components(*chat_history_state.listeners)


def ChatBubble(speaker: str, message: str) -> Div:  # noqa: N802
    """Create a chat bubble for the given speaker and message.

    Args:
        speaker: Either 'user' or 'bot' to determine bubble styling
        message: The text content of the chat message

    Returns:
        Div: A styled chat bubble component with icon and message text
    """
    if speaker == "user":
        return Div(
            Div(
                Icon(USER_ICON, css="w-5 h-5 mr-2"),
                Text(message, css="text-white"),
                css="flex items-center justify-end gap-2",
            ),
            css="bg-blue-500 p-3 rounded-lg max-w-xs self-end",
        )
    else:
        return Div(
            Div(
                Icon(LIGHTBULB_ICON, css="w-5 h-5 mr-2"),
                Text(message, css="text-white"),
                css="flex items-center justify-start gap-2",
            ),
            css="bg-gray-500 p-3 rounded-lg max-w-xs self-start",
        )


def ChatHistory() -> Div:  # noqa: N802
    """Create the chat history display component.

    Renders all chat bubbles from the chat history state and updates
    when new messages are added.

    Returns:
        Div: A container with all chat bubble components
    """
    chat_history = chat_history_state.get()
    children = [ChatBubble(speaker, message) for speaker, message in chat_history]
    return Div(
        children,
        css="flex flex-col gap-3 overflow-y-auto",
        listen_to="chat_history_state",
    )


def MessageForm() -> Form:  # noqa: N802
    """Create the chat message input form.

    Returns:
        Form: A form component with input field and submit button
    """
    return Form(
        Input(
            name="message",
            placeholder="Type your question here...",
            css="flex-grow p-3 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500",
        ),
        Button(Icon(ARROW_UP_ICON, css="w-5 h-5"), type="submit"),
        trigger="generate_bot_response",
        css="w-full flex flex-row gap-3",
    )


@app.page("/")
def index():
    """Render the main chat application page.

    Returns:
        Div: The complete chat interface with history and input
    """
    return Div(
        ChatHistory(),
        MessageForm(),
        css=PAGE,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.chat_app:app", host="0.0.0.0", port=8000, reload=True)
