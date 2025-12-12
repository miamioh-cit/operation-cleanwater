import asyncio, random, struct, os
from typing import Dict, Any
from fastapi import FastAPI
import uvicorn
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server.async_io import StartAsyncTcpServer
from snap7.server import Server
from snap7.types import Areas

MODBUS_PORT=int(os.environ.get("MODBUS_PORT","1502"))
S7_PORT=int(os.environ.get("S7_PORT","1102"))
HTTP_PORT=int(os.environ.get("HTTP_PORT","8080"))
PUMP_NAME=os.environ.get("PUMP_NAME","pump1")
CELL_ID=os.environ.get("CELL_ID","cell01")

tags: Dict[str, Any] = {
  "cell_id": CELL_ID,
  "pump": PUMP_NAME,
  "run": True if PUMP_NAME.endswith("1") else False,
  "speed": 50 if PUMP_NAME.endswith("1") else 0,
  "temp_c_x10": 160 if PUMP_NAME.endswith("1") else 150,
  "kpa": 3158 if PUMP_NAME.endswith("1") else 0,
}

def build_modbus_context()->ModbusServerContext:
  store=ModbusSlaveContext(co=ModbusSequentialDataBlock(0,[0]*16),
                          hr=ModbusSequentialDataBlock(0,[0]*32),
                          zero_mode=True)
  return ModbusServerContext(slaves=store,single=True)

async def modbus_writer_loop(ctx:ModbusServerContext)->None:
  slave_id=0x00
  while True:
    ctx[slave_id].setValues(1,0,[1 if tags["run"] else 0])
    ctx[slave_id].setValues(3,0,[int(tags["speed"]),int(tags["temp_c_x10"]),int(tags["kpa"])])
    await asyncio.sleep(0.2)

DB_NUM=1
DB_SIZE=64

def pack_u16(v:int)->bytes: return struct.pack(">H",v & 0xFFFF)
def pack_i16(v:int)->bytes: return struct.pack(">h",int(v))

def set_bit(buf:bytearray,byte_index:int,bit_index:int,value:int)->None:
  mask=1<<bit_index
  if value: buf[byte_index]|=mask
  else: buf[byte_index]&=~mask

async def s7_server_task()->None:
  srv=Server()
  db=bytearray(DB_SIZE)
  srv.register_area(Areas.DB,DB_NUM,db)
  srv.start(tcpport=S7_PORT)
  try:
    while True:
      set_bit(db,0,0,1 if tags["run"] else 0)
      db[2:4]=pack_u16(int(tags["speed"]))
      db[4:6]=pack_i16(int(tags["temp_c_x10"]))
      db[6:8]=pack_u16(int(tags["kpa"]))
      await asyncio.sleep(0.2)
  finally:
    srv.stop(); srv.destroy()

async def simulation_loop()->None:
  while True:
    sp=max(0,min(100,int(tags["speed"])))
    if tags["run"]:
      tags["kpa"]=int(500+(sp*55)+random.randint(-30,30))
      tags["temp_c_x10"]=int(150+(sp*0.2)+random.randint(-2,2))
    else:
      tags["kpa"]=max(0,int(tags["kpa"])-random.randint(50,120))
      tags["temp_c_x10"]=max(120,int(tags["temp_c_x10"])-random.randint(1,3))
    await asyncio.sleep(1.0)

api=FastAPI()

@api.get("/health")
def health(): return {"ok":True,"cell":CELL_ID,"pump":PUMP_NAME}

@api.get("/local/tags")
def local_tags(): return tags

async def main()->None:
  ctx=build_modbus_context()
  tasks=[
    asyncio.create_task(simulation_loop()),
    asyncio.create_task(modbus_writer_loop(ctx)),
    asyncio.create_task(s7_server_task()),
    asyncio.create_task(StartAsyncTcpServer(context=ctx,address=("0.0.0.0",MODBUS_PORT))),
  ]
  server=uvicorn.Server(uvicorn.Config(api,host="0.0.0.0",port=HTTP_PORT,log_level="warning"))
  tasks.append(asyncio.create_task(server.serve()))
  await asyncio.gather(*tasks)

if __name__=="__main__":
  asyncio.run(main())
