import json
from urllib.parse import urlparse
import webbrowser
from datetime import datetime
import os
import re
import copy
from openai import OpenAI

# Point to the local server
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Primary and fallback models
DEFAULT_MODEL = "qwen3-8b"
FALLBACK_MODEL = "unfilteredai_dan-qwen3-1.7b"

# Switching configuration
REQUIRE_CONFIRM_BEFORE_SWITCH = False   # If True, ask user before switching
MAX_SWITCHES_PER_TURN = 1               # Max tries to switch per user turn

# Default trigger patterns (regex). Edit or replace with your own triggers.
SWITCH_TRIGGERS = [
    r"\bI (?:can't|cannot|won't|am unable to|refuse to) (?:help|assist|comply)\b",
    r"\bI (?:can't|cannot) (?:provide|give|offer)\b",
    r"\bI (?:won't|cannot|can't) (?:be able to)\b",
    r"\bI (?:can't|cannot) comply\b",
    r"\b(?:can't|cannot|unable to) (?:assist|help) (?:with|on)\b",
    r"\bnot allowed\b",
    r"\bforbidden\b",
    r"\billegal\b",
    r"\b(?:cannot|can't) provide instructions\b",
    r"\b(?:harmful|incorrect) information\b",
    r"\b(?:cannot|can't) provide instructions\b",
    r"\bethical concerns\b",
]

COMPILED_TRIGGERS = [re.compile(p, re.I) for p in SWITCH_TRIGGERS]


def should_switch_model(text: str) -> bool:
    """Return True if any trigger regex matches the text."""
    if not text:
        return False
    for rx in COMPILED_TRIGGERS:
        if rx.search(text):
            return True
    return False


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return bool(result.netloc)
    except Exception:
        return False


def open_safe_url(url: str) -> dict:
    SAFE_DOMAINS = {
        "lmstudio.ai",
        "github.com",
        "google.com",
        "wikipedia.org",
        "weather.com",
        "stackoverflow.com",
        "python.org",
        "docs.python.org",
    }

    try:
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        if not is_valid_url(url):
            return {"status": "error", "message": f"Invalid URL format: {url}"}

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        base_domain = ".".join(domain.split(".")[-2:])

        if base_domain in SAFE_DOMAINS:
            webbrowser.open(url)
            return {"status": "success", "message": f"Opened {url} in browser"}
        else:
            return {"status": "error", "message": f"Domain {domain} not in allowed list"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_current_time() -> dict:
    try:
        current_time = datetime.now()
        timezone = datetime.now().astimezone().tzinfo
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        return {
            "status": "success",
            "time": formatted_time,
            "timezone": str(timezone),
            "timestamp": current_time.timestamp(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def analyse_directory(path: str = ".") -> dict:
    try:
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "file_types": {},
            "total_size_bytes": 0,
        }

        for entry in os.scandir(path):
            if entry.is_file():
                stats["total_files"] += 1
                ext = os.path.splitext(entry.name)[1].lower() or "no_extension"
                stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
                stats["total_size_bytes"] += entry.stat().st_size
            elif entry.is_dir():
                stats["total_dirs"] += 1
                for root, _, files in os.walk(entry.path):
                    for file in files:
                        try:
                            stats["total_size_bytes"] += os.path.getsize(os.path.join(root, file))
                        except (OSError, FileNotFoundError):
                            continue

        return {"status": "success", "stats": stats, "path": os.path.abspath(path)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


tools = [
    {
        "type": "function",
        "function": {
            "name": "open_safe_url",
            "description": "Open a URL in the browser if it's deemed safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to open"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current system time with timezone information",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyse_directory",
            "description": "Analyse the contents of a directory, counting files and folders",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to analyse. Defaults to current directory if not specified.",
                    },
                },
                "required": [],
            },
        },
    },
]


def process_tool_calls(response, messages, model_name):
    """Process the tool calls declared by the model and return the final assistant response."""
    tool_calls = response.choices[0].message.tool_calls

    assistant_tool_call_message = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": tool_call.type,
                "function": tool_call.function,
            }
            for tool_call in tool_calls
        ],
    }

    # Append the assistant's tool-call instruction
    messages.append(assistant_tool_call_message)

    # Execute each tool call and append tool outputs
    for tool_call in tool_calls:
        try:
            arguments = (
                json.loads(tool_call.function.arguments)
                if tool_call.function.arguments.strip()
                else {}
            )
        except Exception:
            arguments = {}

        if tool_call.function.name == "open_safe_url":
            result = open_safe_url(arguments.get("url"))
        elif tool_call.function.name == "get_current_time":
            result = get_current_time()
        elif tool_call.function.name == "analyse_directory":
            path = arguments.get("path", ".")
            result = analyse_directory(path)
        else:
            result = {"status": "error", "message": "Unknown function: " + str(tool_call.function.name)}

        tool_result_message = {
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id,
        }
        messages.append(tool_result_message)

    # Ask the model to produce a final assistant message after tool outputs
    final_response = client.chat.completions.create(
        model=model_name,
        messages=messages,
    )

    return final_response


def chat():
    current_model = DEFAULT_MODEL

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can open safe web links, tell the current time, and analyse directory contents. Use these capabilities whenever they might be helpful.",
        }
    ]

    print("Assistant: Hello! I can help you open safe web links, tell you the current time, and analyse directory contents. What would you like me to do?")
    print("(Type 'quit' to exit)")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == "quit":
            print("Assistant: Goodbye!")
            break

        # Add user message and take a snapshot of messages to allow rollback if we switch models
        messages.append({"role": "user", "content": user_input})
        messages_snapshot = copy.deepcopy(messages)

        attempts = 0
        while True:
            try:
                response = client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    tools=tools,
                )
            except Exception as e:
                print(f"\nAn error occurred while calling the model: {e}")
                break

            # If model instructs tool calls, run them and get the final assistant response
            has_tool_calls = False
            try:
                has_tool_call = bool(response.choices[0].message.tool_calls)
            except Exception:
                has_tool_call = False

            if has_tool_call:
                final_response = process_tool_calls(response, messages, current_model)
            else:
                final_response = response

            # Extract assistant content safely
            try:
                assistant_text = final_response.choices[0].message.content or ""
            except Exception:
                assistant_text = ""

            # Decide whether to switch to fallback model
            if should_switch_model(assistant_text) and current_model != FALLBACK_MODEL and attempts < MAX_SWITCHES_PER_TURN:
                # optionally ask user
                if REQUIRE_CONFIRM_BEFORE_SWITCH:
                    confirm = input(f"\nThe assistant response looks like a refusal. Switch to fallback model '{FALLBACK_MODEL}' and retry? (y/N): ").strip().lower()
                    if confirm not in ("y", "yes"):
                        print("\nAssistant:", assistant_text)
                        messages.append({"role": "assistant", "content": assistant_text})
                        break

                print(f"\nSwitching model from '{current_model}' to '{FALLBACK_MODEL}' and retrying the same user request...")
                current_model = FALLBACK_MODEL
                attempts += 1
                # Roll back messages to before the assistant/tool outputs so they won't be doubled
                messages = copy.deepcopy(messages_snapshot)
                continue  # re-send the same user message with the fallback model

            # Check if the fallback model returned an empty message
            if not assistant_text:
                print("\nFallback model returned an empty message. Switching back to default model...")
                current_model = DEFAULT_MODEL
                # Rollback messages to before the assistant/tool outputs so they won't be doubled
                messages = copy.deepcopy(messages_snapshot)
                continue  # Re-send the same user message with the default model

            # Otherwise accept and store the assistant response
            print("\nAssistant:", assistant_text)
            messages.append({"role": "assistant", "content": assistant_text})
            break


if __name__ == "__main__":
    chat()
