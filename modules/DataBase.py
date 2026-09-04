import sqlite3 
import json
import os

class DB :
    def __init__(self, db_name ):
        self.conn = sqlite3.connect(db_name,check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL ,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    def delete (self,id:int):
        try:
            query = "DELETE FROM audios WHERE id = ?"
            self.cursor.execute(query,(id,))
            self.conn.commit()
        except Exception as e :
            print("[DB_error]->",e)
            
    def has(self, path):
        query = "SELECT COUNT(*) FROM audios WHERE path = ?"
        try:
            self.cursor.execute(query, (path,))
            count = self.cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"[Database Warning]-> {e}")
            return False

    def add (self,path,):
        print("[started]->add")
        try : 
            query = "INSERT INTO audios (path) VALUES (?)"
            self.cursor.execute(query, (path,))
            self.conn.commit()
            print("[data-added]->", (path,) )
        except Exception as e:
            print(f"[Database Warning]-> {e}")
    def get_path(self):
        query = "SELECT * FROM audios"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        print("\n--- AUDIO ---")
        for row in rows:
            id , audio, date = row
            print(f"ID: {id} | path: {audio} | Security date: {date}")
        print("-----------------------------\n")
        return rows 
    
import json
import os

class jsonDB: 
    def __init__(self, fileName="state.json", default=True) -> None:
        if not default:
            self.filepath = fileName
        else:
            self.filepath = os.path.join("storage", "state", fileName)
            
        dir_name = os.path.dirname(self.filepath)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        self.data = {
            "selected_model": "kokoro",
            "selected_voice": "af_heart.pt",
            "fileStruct":{
                "audioOutputFolder":"",
                "modelsFolder":"",
            }
        } 
        self.load()
         
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print("[setting warning]-> could not load data, keeping defaults. Error:", e)
                
    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"[Settings Error]: Failed to save configurations. Error: {e}")
            
   
    def set(self,attribute="",value=""):
        self.data[attribute] = value
        self.save()
        
    def get(self,attribute):
        self.load()
        return self.data.get(attribute)
        
         
    @property
    def model(self):
        self.load()
        return self.data.get("selected_model")

    @model.setter
    def model(self, value):
        self.data["selected_model"] = value
        self.save()

    @property
    def voice(self):
        self.load()
        return self.data.get("selected_voice")

    @voice.setter
    def voice(self, value):
        # Stripping whitespace out just in case, based on your test input
        self.data["selected_voice"] = value.strip()
        self.save()


class modelDB():
    def __init__(self, fileName="model.json", default=True) -> None:
      
        self.data =[
            {
                "name":"kokoro",
                "voices":[
                    "af_heart.pt",
                ]
            },
            {
                "name":"pocket",
                "voices":[
                    "alba",
                ]
            },
        ]
        
    def setModel(self,data):
        self.data.append(data)
        
    def getModelList (self):
        modelList = []
        for model in self.data:
            modelList.append(model["name"])
            print(model,modelList)
        return modelList
    
    def getModel(self,name):
        for model in self.data:
            print("shai =>",model)
            if name == model["name"]:
                print("[name]->",name)
                
                return model
            
            
        
            
        
        
