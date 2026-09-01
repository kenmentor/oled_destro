import os
class Helpers :
    def __init__(self) :
        pass 
    def deleteFile(self,path:str):
        if os.path.exists(path):
            os.remove(path)
            print("[helper]->deleted",path)
        else:
            print("[helper]-> file not found")
        
    