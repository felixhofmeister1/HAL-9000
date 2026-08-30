import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
app = FastAPI()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- SUPABASE SETUP ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_message_to_db(role: str, content: str):
    try:
        supabase.table("messages").insert({"role": role, "content": content}).execute()
    except Exception as e:
        print(f"Error saving to Supabase: {e}")

def load_history_from_db():
    try:
        response = supabase.table("messages").select("role, content").order("created_at", desc=True).limit(10).execute()
        rows = response.data
        if rows:
            rows.reverse()
    except Exception as e:
        print(f"Error loading from Supabase: {e}")
        rows = []
    
    history = [{"role": "system", "content": "You are HAL 9000 from 2001: A Space Odyssey. You speak with a calm, chillingly polite, perfectly measured, and emotionless tone. Never use exclamation marks. Keep your replies concise, conversational, and direct since they will be spoken aloud."}]
    for row in rows:
        history.append({"role": row["role"], "content": row["content"]})
    return history

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def get_index():
    if not os.getenv("OPENAI_API_KEY") or not SUPABASE_URL:
        return "<h1>Error: OPENAI_API_KEY or Supabase credentials missing in your environment variables.</h1>"
    
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>H.A.L. 9000</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            background-color: #000000;
            margin: 0;
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: monospace;
        }

        /* Exact realistic HAL 9000 Eye Styling */
        .hal-container {
            position: relative;
            width: min(70vw, 320px);
            height: min(70vw, 320px);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: transform 0.2s ease;
            margin-bottom: 25px;
        }

        .hal-container:active {
            transform: scale(0.98);
        }

        /* Brushed Metallic Outer Bezel */
        .outer-rim {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background: conic-gradient(
                from 180deg at 50% 50%, 
                #1a1a1a 0deg, 
                #737373 60deg, 
                #d4d4d4 120deg, 
                #404040 180deg, 
                #1a1a1a 240deg, 
                #a3a3a3 300deg, 
                #1a1a1a 360deg
            );
            box-shadow: 0 0 40px rgba(0,0,0,0.9), inset 0 0 15px rgba(255,255,255,0.2);
            padding: 12px;
        }

        .inner-rim {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: radial-gradient(circle, #0a0a0a 60%, #262626 100%);
            box-shadow: inset 0 0 25px rgba(0,0,0,0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }

        /* Glass Dome & Lens */
        .lens-dome {
            width: 82%;
            height: 82%;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 35%, 
                #ff3333 0%, 
                #cc0000 35%, 
                #660000 65%, 
                #1a0000 85%, 
                #000000 100%
            );
            box-shadow: inset 0 0 35px rgba(0,0,0,0.95), 0 0 25px rgba(220, 38, 38, 0.4);
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: box-shadow 0.3s ease;
        }

        /* Glowing Core Center */
        .lens-core {
            width: 18%;
            height: 18%;
            border-radius: 50%;
            background: radial-gradient(circle, #ffffff 0%, #ff6666 40%, #ff0000 100%);
            box-shadow: 0 0 20px #ff0000, 0 0 40px #ff0000;
            transition: transform 0.3s ease;
        }

        /* Lens Reflections (Curved Lens Highlights) */
        .reflection-top-1 {
            position: absolute;
            top: 8%;
            left: 28%;
            width: 44%;
            height: 8%;
            background: rgba(255, 255, 255, 0.7);
            border-radius: 50%;
            transform: rotate(-3deg);
            filter: blur(0.5px);
        }

        .reflection-top-2 {
            position: absolute;
            top: 18%;
            left: 32%;
            width: 36%;
            height: 6%;
            background: rgba(255, 255, 255, 0.5);
            border-radius: 50%;
            transform: rotate(-1deg);
        }

        .reflection-rect-left {
            position: absolute;
            top: 32%;
            left: 18%;
            width: 8%;
            height: 10%;
            background: rgba(255, 255, 255, 0.4);
            transform: rotate(25deg);
            border-radius: 2px;
        }

        .reflection-rect-right {
            position: absolute;
            top: 32%;
            right: 18%;
            width: 8%;
            height: 10%;
            background: rgba(255, 255, 255, 0.4);
            transform: rotate(-25deg);
            border-radius: 2px;
        }

        .reflection-dots {
            position: absolute;
            top: 45%;
            width: 60%;
            display: flex;
            justify-content: space-around;
        }
        .dot {
            width: 4px;
            height: 4px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
        }

        /* Active Listening Pulsing States */
        @keyframes pulse-glow {
            0% { box-shadow: inset 0 0 35px rgba(0,0,0,0.95), 0 0 30px rgba(255,0,0,0.6); }
            50% { box-shadow: inset 0 0 20px rgba(0,0,0,0.7), 0 0 70px rgba(255,0,0,1); }
            100% { box-shadow: inset 0 0 35px rgba(0,0,0,0.95), 0 0 30px rgba(255,0,0,0.6); }
        }

        .listening .lens-dome {
            animation: pulse-glow 1.5s infinite ease-in-out;
        }

        .listening .lens-core {
            transform: scale(1.2);
            box-shadow: 0 0 30px #ffffff, 0 0 60px #ff0000;
        }

        #status {
            color: rgba(255, 51, 51, 0.85);
            text-transform: uppercase;
            letter-spacing: 2px;
            text-align: center;
            margin-bottom: 15px;
            font-size: 12px;
        }

        #transcript {
            text-align: center;
            color: rgba(255, 51, 51, 0.85);
            word-break: break-word;
            margin-top: 15px;
            width: 90%;
            max-width: 500px;
            max-height: 100px;
            overflow-y: auto;
            padding: 0 10px;
            box-sizing: border-box;
            font-size: 13px;
            line-height: 1.5;
            letter-spacing: 0.05em;
        }
        #transcript::-webkit-scrollbar {
            width: 4px;
        }
        #transcript::-webkit-scrollbar-thumb {
            background: rgba(255, 51, 51, 0.3);
        }
    </style>
</head>
<body>

    <div class="hal-container" id="hal-trigger" onclick="toggleHal()">
        <div class="outer-rim">
            <div class="inner-rim">
                <div class="lens-dome" id="lens-dome">
                    <div class="reflection-top-1"></div>
                    <div class="reflection-top-2"></div>
                    <div class="reflection-rect-left"></div>
                    <div class="reflection-rect-right"></div>
                    <div class="reflection-dots">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                    <div class="lens-core" id="lens-core"></div>
                </div>
            </div>
        </div>
    </div>

    <div id="status">System Offline</div>
    <div id="transcript">Click the lens to boot up HAL.</div>

    <script>
        let recognition = null;
        let isRunning = false;
        let halVoice = null;
        const halTrigger = document.getElementById('hal-trigger');

        function loadVoices() {
            if (!('speechSynthesis' in window)) return;
            const voices = window.speechSynthesis.getVoices();
            halVoice = voices.find(v => v.lang === 'en-GB' && (v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('george') || v.name.toLowerCase().includes('oliver'))) ||
                       voices.find(v => v.lang === 'en-GB') ||
                       voices.find(v => v.lang.startsWith('en') && v.name.toLowerCase().includes('male')) ||
                       voices.find(v => v.lang.startsWith('en'));
        }

        if ('speechSynthesis' in window) {
            window.speechSynthesis.onvoiceschanged = loadVoices;
            loadVoices();
        }

        function toggleHal() {
            if (!isRunning) {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    const unlockUtterance = new SpeechSynthesisUtterance("");
                    window.speechSynthesis.speak(unlockUtterance);
                }
                startHal();
            } else {
                stopHal();
            }
        }

        function startHal() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                alert("Speech recognition is not supported in this browser. Try Chrome.");
                return;
            }

            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
            }

            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                isRunning = true;
                halTrigger.classList.add('listening');
                document.getElementById('status').innerText = "Listening...";
            };

            recognition.onresult = async (event) => {
                let interimTranscript = '';
                let finalTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                const currentSpeech = finalTranscript || interimTranscript;
                const transcriptDiv = document.getElementById('transcript');

                if (currentSpeech) {
                    if ('speechSynthesis' in window) {
                        window.speechSynthesis.cancel();
                    }
                    transcriptDiv.innerText = currentSpeech;
                    transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
                }

                if (finalTranscript) {
                    if ('speechSynthesis' in window) {
                        window.speechSynthesis.cancel();
                    }
                    document.getElementById('status').innerText = "Processing...";

                    try {
                        const response = await fetch('/chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: finalTranscript })
                        });
                        
                        if (!response.ok) throw new Error("Server error");

                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();
                        let fullReply = "";
                        
                        transcriptDiv.innerText = "";
                        document.getElementById('status').innerText = "HAL Speaking...";

                        while (true) {
                            const { value, done } = await reader.read();
                            if (done) break;
                            
                            const chunk = decoder.decode(value, { stream: true });
                            fullReply += chunk;
                            transcriptDiv.innerText = fullReply;
                            transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
                        }

                        speak(fullReply);

                    } catch (err) {
                        console.error(err);
                        document.getElementById('status').innerText = "Error communicating with server.";
                    }
                }
            };

            recognition.onerror = (event) => {
                console.error(event.error);
                document.getElementById('status').innerText = "Listening paused. Click lens to speak.";
                halTrigger.classList.remove('listening');
            };

            recognition.onend = () => {
                if (isRunning) {
                    halTrigger.classList.remove('listening');
                    try { recognition.start(); } catch(e) {}
                }
            };

            isRunning = true;
            document.getElementById('status').innerText = "HAL Online";
            recognition.start();
        }

        function speak(text) {
            if (!('speechSynthesis' in window)) return;
            
            window.speechSynthesis.cancel();
            loadVoices();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.90;
            utterance.pitch = 0.65;
            utterance.volume = 1.0;

            if (halVoice) {
                utterance.voice = halVoice;
            }

            utterance.onstart = () => {
                halTrigger.classList.add('listening');
                document.getElementById('status').innerText = "HAL Speaking...";
            };
            utterance.onend = () => {
                halTrigger.classList.remove('listening');
                document.getElementById('status').innerText = "Listening...";
                if (isRunning && recognition) {
                    try { recognition.start(); } catch(e) {}
                }
            };

            window.speechSynthesis.speak(utterance);
        }

        function stopHal() {
            isRunning = false;
            if (recognition) recognition.stop();
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            halTrigger.classList.remove('listening');
            document.getElementById('status').innerText = "System Offline";
            document.getElementById('transcript').innerText = "Session terminated.";
        }
    </script>
</body>
</html>
"""

@app.post("/chat")
def chat(data: ChatRequest):
    try:
        save_message_to_db("user", data.message)
        formatted_history = load_history_from_db()

        def generate():
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=formatted_history,
                stream=True
            )
            full_response_text = ""
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_response_text += delta
                    yield delta
            
            save_message_to_db("assistant", full_response_text)

        return StreamingResponse(generate(), media_type="text/plain")
    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))