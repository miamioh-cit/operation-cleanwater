import asyncio, time, yaml
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pymodbus.client import ModbusTcpClient

CFG_PATH="/app/plcs.yaml"
cfg=yaml.safe_load(open(CFG_PATH,"r"))
PLCS=cfg.get("plcs",[])
MODBUS_PORT_DEFAULT=int(cfg["defaults"]["modbus_port"])

state: Dict[str, Any] = {"updated_at": None, "cells": {}}

app=FastAPI()
app.mount("/static", StaticFiles(directory="/app/web"), name="static")

@app.get("/")
def root():
  return FileResponse("/app/web/index.html")

def read_modbus(ip:str, port:int)->Dict[str,Any]:
  c=ModbusTcpClient(ip,port=port,timeout=1.0)
  if not c.connect():
    raise ConnectionError("modbus connect failed")
  rr_co=c.read_coils(0,1)
  rr_hr=c.read_holding_registers(0,3)
  c.close()
  return {
    "run": bool(rr_co.bits[0]) if rr_co and rr_co.bits else False,
    "speed": rr_hr.registers[0] if rr_hr and rr_hr.registers else 0,
    "temp_c_x10": rr_hr.registers[1] if rr_hr and rr_hr.registers else 0,
    "kpa": rr_hr.registers[2] if rr_hr and rr_hr.registers else 0,
  }

def cell_aggregate(p1:Dict[str,Any], p2:Dict[str,Any])->Dict[str,Any]:
  flow=0
  if p1.get("run"): flow += int(p1.get("speed",0)*0.4)
  if p2.get("run"): flow += int(p2.get("speed",0)*0.4)
  flow=max(0,min(50,flow))
  pin=max(int(p1.get("kpa",0)), int(p2.get("kpa",0)))
  pout=int(pin*1.15) if pin else 0
  return {"flow_rate":flow,"pressure_in":pin,"pressure_out":pout,"dirty_filters":False,"control_valves":True}

async def poll_loop():
  while True:
    cells: Dict[str, Any] = {}
    now=time.time()
    for plc in PLCS:
      cell=plc["cell"]; pump=plc["pump"]; ip=plc["ip"]
      port=int(plc.get("modbus_port", MODBUS_PORT_DEFAULT))
      cells.setdefault(cell, {"pumps": {}, "process": {}, "errors": []})
      try:
        cells[cell]["pumps"][pump]=read_modbus(ip,port)
      except Exception as e:
        cells[cell]["errors"].append({pump: str(e)})
    for cell_id, cobj in cells.items():
      p1=cobj["pumps"].get("pump1", {"run":False,"speed":0,"temp_c_x10":0,"kpa":0})
      p2=cobj["pumps"].get("pump2", {"run":False,"speed":0,"temp_c_x10":0,"kpa":0})
      cobj["process"]=cell_aggregate(p1,p2)
    state["cells"]=cells
    state["updated_at"]=now
    await asyncio.sleep(1.0)

@app.get("/api/tags")
def tags():
  return state

@app.get("/api/cells/{cell_id}")
def cell(cell_id:str):
  c=state["cells"].get(cell_id)
  if not c: raise HTTPException(404, f"Unknown cell {cell_id}")
  return {"cell": cell_id, **c}

if __name__=="__main__":
  loop=asyncio.get_event_loop()
  loop.create_task(poll_loop())
  uvicorn.run(app, host=cfg["gateway"]["bind"], port=int(cfg["gateway"]["port"]))
