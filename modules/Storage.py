class Storage:
    def __init__ (self,file_path):
        pass 
    def fetchData (self):
        pass 
    def addData (self):
        pass 
    def deleteData(self):
        pass 
    def updateData (self):
        pass 


class AudioStorage (Storage) :
    def __init__ (self,audio_storage_path):
        super().__init__(audio_storage_path)
    def save_audio (self,audio_path,):
        pass