import { useState } from "react";

import { invoke } from "@tauri-apps/api/core";
import {save} from "@tauri-apps/plugin-dialog"
import { open } from "@tauri-apps/plugin-dialog";
import {Command} from "@tauri-apps/plugin-shell"
import {writeFile } from "@tauri-apps/plugin-fs"


import "./App.css";
import { File, History, SearchAlertIcon, Settings, Upload } from "lucide-react";

function App() {
  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");
  const [selectedFile ,setSelectedFile ] = useState(null)

async function handlePick(){
  const selectedPath = await open({
    multiple:false,
    filters:[{name:"PDF",extensions:["pdf"]}]
  })
  console.log(selectedPath)
}
  
  return (
    <main className="container">
      <h1>Convert PDF To Audio</h1>
      {/* <div className="sidebar">
        <button>
          <Settings/>
        </button>
         <button>
          <History/>
        </button>
        
        
        </div>     */}
    <div>
<button onClick={handlePick}><Upload/> </button> 
    </div>
      
        
  
   
    </main>
  );
}

export default App;
