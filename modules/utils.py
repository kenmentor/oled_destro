import os 
import uuid 


class Utils :
    def __init__ (self,file_path=None ,voice_path = None):
        self.file_path = file_path 
        self.voice_path = voice_path
    def get_voice(self,file_path =None ):
        if  file_path == None :
            file_path = self.voice_path 
        return os.listdir(file_path)
    def filterDoc(self,text:str):
        return text.replace(["\n",]," ")
    def download_audio(audio_path ,download_locarion):
        pass 
    def delete_audio(audio_path):
        pass
    def update_audio(audio_path ,new_audio):
        pass
    def save_audio():
        pass