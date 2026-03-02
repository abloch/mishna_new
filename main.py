import uvicorn
from datetime import date, timedelta
from os import environ
from fastapi import FastAPI

import persistance
from get_mishna import main as get_mishna_main, parse_config
from is_yomtov import is_holiday

today = date.today()
tomorrow = today + timedelta(days=1)

app = FastAPI()

@app.get("/")
@app.get("/health")
async def root():
    return {"health": True}

@app.get("/mishna")
async def get_mishna(noon: bool = False):
    if is_holiday(today):
        return {"message": "Today is a holiday!"}
    if noon and is_holiday(tomorrow):
        return {"message": "Tomorrow is a holiday!"}
    get_mishna_main()
    return {"message": "Mishna fetched successfully!", "status": "success", "noon": noon}

if __name__ == "__main__":
    portstr = environ.get("PORT", "8080")
    port = int(portstr)
    uvicorn.run(app, host="0.0.0.0", port=port)
