from fastapi import FastAPI

app = FastAPI(title="Gestionale Birrificio")

@app.get("/")
def home():
    return {"status": "ok", "app": "Gestionale Birrificio"}
