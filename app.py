@app.post("/reset")
async def reset(task: str = "easy"):
    return {"observation": f"KubeSRE {{task}} incident started. Health: 100%", "reward": None, "done": False}

@app.post("/step") 
async def step(action: dict):
    return {"observation": "Action executed", "reward": 0.1, "done": False}

@app.get("/health")
async def health():
    return {"status": "healthy"}
