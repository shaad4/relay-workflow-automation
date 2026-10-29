import asyncio

from fastapi import FastAPI

app = FastAPI()


@app.get("/delay")
async def delay():
    await asyncio.sleep(3)
    return {"success": True}


@app.get("/delay-10")
async def delay_10():
    await asyncio.sleep(10)
    return {"success": True}