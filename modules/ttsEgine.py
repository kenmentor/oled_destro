import torch
import numpy as np
import os
from kokoro import KPipeline
from kokoro.model import KModel
import scipy.io.wavfile 
from pocket_tts import TTSModel
from modules.DataBase import jsonDB

stateDB = jsonDB()



#BASE CLASS
class MODEL:
    def __init__(self, device=None):
        self.default_voice= str()
    def get_model(self,name,config=None)->object:
        pass
    def synthesize(self, text, voice=None):
        pass
    
    
#GET MODEL CLASS
class MODEL_EGINE:
    def __init__ (self,module_path=""):
        self.path_base = module_path
        self.default = stateDB.model
        self.modelReferenceList = {
            "kokoro":KOKORO,
            "pocket":POCKET
        }
        # Guard against stale/invalid model ids stored in state
        if self.default not in self.modelReferenceList:
            self.default = next(iter(self.modelReferenceList))
            stateDB.model = self.default
        self.current_model = self.default
        
    def get_model(self,name="pocket",config=None)->MODEL:
        if name not in self.modelReferenceList:
            name = self.default
        self.current_model = name
        return self.modelReferenceList[name]
    
    def load_default(self):
        self.current_model = self.default
        return self.modelReferenceList[self.default]
    
    def add_model(self,model_name,model_class):
        self.modelReferenceList[model_name] = model_class
        
#POCKET
class POCKET(MODEL):
    # Local, pre-installed default voices shipped with the app (no internet needed).
    DEFAULT_VOICES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "modules", "voices", "pocket",
    )

    def __init__(self, device=None):
        self.tts_model = TTSModel.load_model()
        self.tts_model.has_voice_cloning = True
        self.default_voice = self._first_available()
        self._voice_state_cache = {}

    def get_state(self, voice_filename):
        """Return the (cached) conditioner state for a voice prompt."""
        if voice_filename not in self._voice_state_cache:
            self._voice_state_cache[voice_filename] = self.tts_model.get_state_for_audio_prompt(
                voice_filename, truncate=True
            )
        return self._voice_state_cache[voice_filename]

    def _first_available(self):
        """Return the first usable default voice (or first clone)."""
        defaults = self.list_default_voices()
        if defaults:
            return defaults[0]
        try:
            from modules.voiceLibrary import VoiceLibrary
            clones = VoiceLibrary().names()
            return clones[0] if clones else ""
        except Exception as e:
            print(f"[POCKET] unable to enumerate voices: {e}")
            return ""

    @staticmethod
    def list_default_voices():
        """Names of the pre-installed default pocket voices."""
        names = []
        if os.path.isdir(POCKET.DEFAULT_VOICES_DIR):
            for fn in sorted(os.listdir(POCKET.DEFAULT_VOICES_DIR)):
                if fn.lower().endswith(".wav"):
                    names.append(os.path.splitext(fn)[0])
        return names

    @staticmethod
    def default_voice_path(name):
        """Resolve a default-voice name to its local wav file, if present."""
        if not name:
            return None
        path = os.path.join(POCKET.DEFAULT_VOICES_DIR, f"{name}.wav")
        return path if os.path.exists(path) else None

    def get_voice(self, voice_filename=None):
         if voice_filename is None or voice_filename == "":
            voice_filename = self.default_voice or self._first_available()

         if not voice_filename:
             raise ValueError("Pocket TTS requires a voice (no default or clone available)")

         # 1) Default pre-installed voice name -> local .wav.
         default_path = self.default_voice_path(voice_filename)
         if default_path:
             voice_filename = default_path

         # 2) Cloned voices referenced by display name -> resolve to audio file.
         if not os.path.exists(voice_filename):
             from modules.voiceLibrary import VoiceLibrary
             clone_path = VoiceLibrary().source_wav(voice_filename)
             if clone_path and os.path.exists(clone_path):
                 voice_filename = clone_path

         if not os.path.exists(voice_filename):
             raise FileNotFoundError(f"Pocket voice not found locally: {voice_filename}")

         print("[pocket_tts get_voice]->", voice_filename)
         return self.get_state(voice_filename)


    def synthesize(self, text, voice=None):
        print("text ->",text)
        voice_state = self.get_voice(voice)
        print("[voice_state]->",voice_state)
        
        for chunk in self.tts_model.generate_audio_stream(voice_state,text):
            chunk_cpu = chunk.cpu().numpy().squeeze()
            chunk_clamped = np.clip(chunk_cpu,-1.0,1.0)
            chunk_int16 = (chunk_clamped*32767).astype(np.int16)

            yield chunk_int16.tobytes()
            
            
            
#KOKORO
class KOKORO:
    def __init__(self, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.json")
        model_path = os.path.join(base_dir, "kokoro-v1_0.pth")
        self.model = KModel(config=config_path, model=model_path)
        
        if "cuda" in self.device:
            self.model = self.model.half()
            torch.backends.cudnn.benchmark = True 
            
        self.model.to(self.device).eval()
        self.pipeline = KPipeline(
            model=self.model,
            device=self.device,
            lang_code="a",
            repo_id=None,
        )
        self.sample_rate = 24000
        self.default_voice = "pf_dora.pt"
        self._voice_cache = {}
        self.get_voice(self.default_voice)

    def get_voice(self, voice_filename):
        """Internal helper to retrieve voice tensors from memory cache or load on demand."""
        if voice_filename is None:
            voice_filename = self.default_voice

        if voice_filename not in self._voice_cache:
            candidates = [voice_filename]
            if voice_filename != self.default_voice:
                candidates.append(self.default_voice)

            voice_tensor = None
            for candidate in candidates:
                voice_path = f"./modules/voices/{candidate}"

                if not os.path.exists(voice_path):
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    voice_path = os.path.join(base_dir, "voices", candidate)

                if not os.path.exists(voice_path):
                    print(f"[TTSEngine] Voice not found: {candidate}")
                    continue

                print(f"[TTSEngine] Cache Miss. Fetching voice from storage: {candidate}")
                try:
                    voice_tensor = torch.load(voice_path, map_location=self.device)
                    voice_filename = candidate
                    break
                except Exception as e:
                    print(f"[TTSEngine] Failed to load voice {candidate}: {e}")
                    voice_tensor = None

            if voice_tensor is None:
                raise FileNotFoundError(
                    f"No usable voice found for '{voice_filename}' in ./modules/voices"
                )

            if "cuda" in self.device and hasattr(voice_tensor, "half"):
                voice_tensor = voice_tensor.half()

            self._voice_cache[voice_filename] = voice_tensor

        return self._voice_cache[voice_filename]

    @torch.inference_mode() 
    def synthesize(self, text, voice=None):
        """Yields audio raw PCM data packets immediately as individual sentences complete."""
        voice_file = voice if voice else self.default_voice
        print(f"[TTSEngine Streaming Execution] Target Voice Profile: {voice_file}")
        
        # Instantly pluck tensor vector from VRAM/RAM memory registers
        voice_tensor = self.get_voice(voice_file)

        # Run inference stream pipeline
        gen = self.pipeline(text, voice=voice_tensor)

        for _, _, audio in gen:
            if audio is None:
                continue
            
            # Ensure the audio tensor is moved back to host memory space before running NumPy transformations
            if audio.device.type != 'cpu':
                audio = audio.cpu()
            
            np_audio = audio.numpy()
            audio_int16 = (np_audio * 32767).astype(np.int16)
            print(f"[synthesize]-> Generated {len(audio_int16)} samples")

            yield audio_int16.tobytes()
