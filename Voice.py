import speech_recognition as sr
import pyttsx3
import queue
import threading

# =========================
# CORE ENGINE INIT
# =========================
engine = pyttsx3.init()

recognizer = sr.Recognizer()
mic = sr.Microphone()

# =========================
# VOICE SETTINGS (DEFAULT)
# =========================
VOICE_CONFIG = {
    "tone": "friendly",   # friendly | professional | sassy | funny | calm
    "rate": 175,
    "volume": 1.0
}

# =========================
# PERSONALITY SYSTEM (OPEN-ENDED)
# =========================
PERSONALITIES = {

    "friendly": {
        "prefix": "🙂",
        "style": "warm, simple, supportive language"
    },

    "professional": {
        "prefix": "📊",
        "style": "clear, structured, formal language"
    },

    "sassy": {
        "prefix": "😏",
        "style": "slightly humorous, confident, witty tone"
    },

    "funny": {
        "prefix": "😂",
        "style": "light humor, playful tone"
    },

    "calm": {
        "prefix": "🌿",
        "style": "slow, peaceful, minimal emotional intensity"
    }
}

# =========================
# SPEECH ENGINE CONFIG
# =========================
def apply_voice_settings():
    engine.setProperty("rate", VOICE_CONFIG["rate"])
    engine.setProperty("volume", VOICE_CONFIG["volume"])

apply_voice_settings()

# =========================
# TEXT TO SPEECH (MAIN OUTPUT)
# =========================
def speak(text, tone=None):

    if tone is None:
        tone = VOICE_CONFIG["tone"]

    personality = PERSONALITIES.get(tone, PERSONALITIES["friendly"])

    formatted_text = f"{personality['prefix']} {text}"

    engine.say(formatted_text)
    engine.runAndWait()

# =========================
# LISTEN (INPUT LAYER)
# =========================
def listen():

    with mic as source:
        print("🎤 Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print("🗣 You said:", text)
        return text

    except sr.UnknownValueError:
        return "Sorry, I didn't understand."

    except sr.RequestError:
        return "Voice service error."

# =========================
# DYNAMIC TONE CONTROL
# =========================
def set_tone(tone):

    if tone in PERSONALITIES:
        VOICE_CONFIG["tone"] = tone
        return f"Tone set to {tone}"

    return "Tone not found"

# =========================
# VOICE AGENT REGISTRY (PLUG-IN SYSTEM)
# =========================
VOICE_AGENTS = {}

def register_voice_agent(name, function):
    """
    Add new voice behavior WITHOUT editing core system
    """
    VOICE_AGENTS[name] = function

# =========================
# EXECUTE VOICE AGENT
# =========================
def run_voice_agent(name, input_text):

    if name in VOICE_AGENTS:
        return VOICE_AGENTS[name](input_text)

    return None

# =========================
# MAIN VOICE PIPELINE
# =========================
def voice_pipeline():

    text = listen()

    # optional agent trigger format:
    # "agent:weather what's today weather"
    if text.startswith("agent:"):

        try:
            parts = text.split(" ", 1)
            agent_name = parts[0].replace("agent:", "")
            content = parts[1] if len(parts) > 1 else ""

            result = run_voice_agent(agent_name, content)

            if result:
                speak(result)
            else:
                speak("No such voice agent found.")

            return result

        except:
            speak("Voice agent error.")
            return None

    return text
