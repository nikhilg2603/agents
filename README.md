# LiveKit Agent with AI-Powered Interruption Handling

This project implements an advanced, conversational AI agent using the LiveKit Agents framework. It solves the common "filler word" problem by intelligently deciding when to ignore user speech (like "uh" or "umm") and when to accept a real interruption.

This solution is designed to be language-aware by using a configurable list of filler words.

## Core Features

This agent successfully implements all objectives from the SalesCode.ai Challenge:

* **Smart Interruption:** The agent correctly ignores filler words from a defined list ("uh", "umm", "haan", etc.) when it is speaking, allowing it to complete its thought.
* **Real-Time Responsiveness:** The agent stops *immediately* if it detects genuine user speech ("wait", "stop that", "no not that one") while it is talking.
* **Context-Aware:** The *same* filler words ("umm" or "haan") are registered as valid input when the agent is quiet, allowing the user to start a thought naturally.
* **Modular Design:** All interruption logic is cleanly separated into `src/interruption_handler.py` for maintainability. The main `src/agent.py` file only defines the agent's "personality" and logic.
* **Dynamic Filler List (Bonus):** The agent includes tools (`add_ignored_words`, `remove_ignored_words`) that allow the user to dynamically update the filler word list in real-time during the conversation.
* **Multi-Language Support (Bonus):** The default filler list includes words from English and Hindi. The agent's tools allow for adding fillers from any language at runtime.

---

## Setup and Installation

Follow these steps to set up the project environment.

### 1. Prerequisites
* Python 3.10+
* `uv` (a fast Python package manager)
* An OpenAI API key **with billing enabled**.
* A Google AI Studio (Gemini) API key (this is free).

### 2. Environment Setup

1.  **Clone the repository:**
    ```bash
    git clone [git@github.com:nikhilg2603/agents.git](git@github.com:nikhilg2603/agents.git)
    cd agents
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install `uv` (if you don't have it):**
    `uv` is a very fast replacement for `pip`.
    ```bash
    pip install uv
    ```

4.  **Install dependencies using `uv`:**
    This reads the `requirements.txt` file and installs all packages.
    ```bash
    uv sync
    ```
    
    ```bash
    # For macOS/Linux
    source .venv/bin/activate

    # For Windows
    .venv\Scripts\activate
    ```

5.  **Install Audio System Dependencies (Linux Only):**
    If you are on Ubuntu/Debian, the `console` mode requires the PortAudio library to access your microphone.
    ```bash
    sudo apt-get update && sudo apt-get install portaudio19-dev
    ```

6.  **Download VAD Models:**
    The agent requires local models for Voice Activity Detection. Run this command once to download them.
    ```bash
    python src/agent.py download-files
    ```

---

## Configuration (API Keys)

This project is set up to run in `console` mode and requires you to **hardcode your API keys** directly into the main agent file.

1.  **Open the main agent file:**
    Open `src/agent.py`.

2.  **Add your API Keys:**
    Paste your keys into the `.env.local` file. **You must have billing enabled on your OpenAI account** for this agent to work, as it's used for both the main chat and the internal filler-detection.

    ```ini
    # --- LiveKit Project Keys ---
    # (From your LiveKit project settings)
    LIVEKIT_URL=
    LIVEKIT_API_KEY=
    LIVEKIT_API_SECRET=

    ```


    **CRITICAL:** The OpenAI API for STT and TTS is a **paid service**. Your agent will fail with a `429 insufficient_quota` error until you have **enabled billing and added credits** to your OpenAI account. The Google Gemini key is free.

---

## Running the Agent

This agent is configured to run in `console` mode, which uses your local terminal's microphone and speakers.

1.  **Ensure your API keys are in `src/agent.py`** and your `venv` is active.

2.  **Run the agent in `console` mode:**
    ```bash
    python src/agent.py console
    ```

3.  **Wait for Connection:**
    If successful, you will see logs and then:
    ```
    ==================================================
         Livekit Agents - Console
    ==================================================
    Press [Ctrl+B] to toggle between Text/Audio mode, [Q] to quit.
    ```
    Your agent is now running and listening through your microphone.

---

## How to Test

Once the agent is running in `console` mode, you can test the logic by speaking into your microphone.

### Test Scenarios

* **Test 1: Filler While Agent Speaks**
    * **Action:** Ask the agent a question ("What's the capital of France?"). While it is replying ("The capital of France is..."), say "umm..." or "haan...".
    * **Expected:** The agent will *ignore* your filler and continue speaking. Your log will show "Ignored filler...".

* **Test 2: Real Interruption**
    * **Action:** Ask the agent a long question ("Tell me about the history of the Eiffel Tower"). While it is speaking, say "wait, stop, tell me about the Louvre instead."
    * **Expected:** The agent will *stop speaking immediately* and begin responding to your new query.

* **Test 3: Filler While Agent is Quiet**
    * **Action:** When the agent is quiet, start your sentence with a filler. "Umm... what time is it?"
    * **Expected:** The agent will *hear* the entire phrase, including "Umm," and process it as valid input.

* **Test 4: Dynamic List (Bonus)**
    * **Action:** Say "add 'like' to the ignored words list."
    * **Expected:** The agent will confirm the word "like" has been added.
    * **Action:** Ask a question. While the agent speaks, say "like...".
    * **Expected:** The agent will now ignore "like" and continue speaking.

---

## Project Structure

```
.
├── .env.local          # Not used by console mode, but good practice
├── requirements.txt    # Python dependencies (used by 'uv sync')
└── src/
    ├── __init__.py     # Makes 'src' a Python package
    ├── agent.py        # Main file. Defines the Assistant class,
    │                   # its personality, API keys, and
    │                   # filler-word management tools.
    └── interruption_handler.py # Modular logic for handling transcriptions
                                # and deciding when to interrupt.
```