@app.post("/reset")
async def reset(task: str = "easy"):
    return {"observation": f"KubeSRE {{task}} incident started. Health: 100%", "reward": None, "done": False}

@app.post("/step") 
async def step(action: dict):
    return {"observation": "Action executed", "reward": 0.1, "done": False}

@app.get("/health")
async def health():
    return {"status": "healthy"}
  
@app.post("/reset")  
async def reset(task: str = "easy"):  
    return {  
        "observation": f"KubeSRE {task} incident. Health: 100%",  
        "reward": None,  
        "done": False  
    }  

@app.post("/step")  
async def step(action: dict):  
    return {  
        "observation": "Action executed",  
        "reward": 0.1,  
        "done": False  
    }
@app.post("/reset")
async def reset(task: str = "easy"):
    return {
        "observation": f"KubeSRE {{task}} incident started. Health: 100%. Alerts active.",
        "reward": None,
        "done": False
    }

@app.post("/step")
async def step(action: dict):
    return {
        "observation": f"Executed: {{action.get('command', 'unknown')}}. Health improved.",
        "reward": 0.1,
        "done": False
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
