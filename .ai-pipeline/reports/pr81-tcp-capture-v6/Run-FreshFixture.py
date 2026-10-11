"""One fresh original fixture after an independently reviewed manual controller handshake."""
import ast
import ctypes
import ctypes.wintypes as w
import hashlib
import json
import os
import socket
import struct
import sys
import time
import uuid
import winreg
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.dont_write_bytecode=True
run=uuid.UUID(sys.argv[1]) if len(sys.argv)>1 and sys.argv[1]!="--validate" else None
def host_hash():
 with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\Microsoft\Cryptography") as key:value=winreg.QueryValueEx(key,"MachineGuid")[0]
 return hashlib.sha256(value.encode()).hexdigest()
def verify():
 snapshot=json.loads((ROOT/"tmp/pr81-tcp-trace-preparation-start.json").read_text())
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in snapshot["preserved_hashes"].items())
 bundle=json.loads((Path(__file__).parent/"bundle.json").read_text())
 assert all(hashlib.sha256((Path(__file__).parent/p).read_bytes()).hexdigest()==h for p,h in bundle["files"].items())
 assert host_hash()==bundle["host_hash"]
 return snapshot,bundle
# Read-only SO_PROTOCOL_INFOW (0x2005); exact Windows SDK WSAPROTOCOL_INFOW layout.
class ProtocolChain(ctypes.Structure):
 _fields_=[("length",w.INT),("entries",w.DWORD*7)]
class ProtocolInfo(ctypes.Structure):
 _fields_=[("service_flags",w.DWORD*4),("provider_flags",w.DWORD),("provider_id",ctypes.c_ubyte*16),("catalog",w.DWORD),("chain",ProtocolChain),("version",w.INT),("family",w.INT),("max_address",w.INT),("min_address",w.INT),("socket_type",w.INT),("protocol",w.INT),("protocol_max_offset",w.INT),("byte_order",w.INT),("security",w.INT),("message_size",w.DWORD),("reserved",w.DWORD),("name",ctypes.c_uint16*256)]
assert ctypes.sizeof(ProtocolInfo)==628 and ProtocolInfo.family.offset==76 and ProtocolInfo.socket_type.offset==88 and ProtocolInfo.protocol.offset==92
def protocol_fields(raw):
 if len(raw)!=628:raise ValueError("NATIVE_PROTOCOL_LAYOUT")
 info=ProtocolInfo.from_buffer_copy(raw)
 return {"family":info.family,"type":info.socket_type,"protocol":info.protocol}
def accepted_protocol(sock):
 try:return {"status":"MEASURED","numeric_error":0,**protocol_fields(sock.getsockopt(socket.SOL_SOCKET,0x2005,628))}
 except OSError as error:return {"status":"UNKNOWN","numeric_error":getattr(error,"winerror",None) or error.errno,"family":None,"type":None,"protocol":None}
 except ValueError:return {"status":"UNKNOWN","numeric_error":None,"family":None,"type":None,"protocol":None}

snapshot,bundle=verify()
if run is None:
 ast.parse(Path(__file__).read_text())
 fake=bytearray(628);struct.pack_into("<i",fake,76,2);struct.pack_into("<i",fake,88,1);struct.pack_into("<i",fake,92,6);fake[116:128]=b"private-name"
 assert protocol_fields(fake)=={"family":2,"type":1,"protocol":6}
 for bad in (b"",bytes(627),bytes(629)):
  try:protocol_fields(bad)
  except ValueError:pass
  else:raise AssertionError("protocol layout rejection missing")
 class FakeSocket:
  def getsockopt(self,*args):raise OSError(22,"private exception text")
 assert accepted_protocol(FakeSocket())=={"status":"UNKNOWN","numeric_error":22,"family":None,"type":None,"protocol":None}
 print("Runner validation PASS; no fixture/trace executed");raise SystemExit(0)
control=ROOT/f"tmp/pr81-tcp-capture-control/{run}"
armed=json.loads((control/"armed.json").read_text())
assert armed["run_id"]==str(run) and armed["host_hash"]==host_hash() and armed["profile_sha256"]==bundle["profile_sha256"]
kernel=ctypes.WinDLL("kernel32",use_last_error=True)
kernel.GetCurrentProcess.restype=w.HANDLE
kernel.GetTickCount64.restype=ctypes.c_ulonglong
kernel.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
times=[w.FILETIME() for _ in range(4)]
assert kernel.GetProcessTimes(kernel.GetCurrentProcess(),*(ctypes.byref(t) for t in times))
creation=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
def put(path,value):
 with path.open("x",encoding="utf-8") as out:json.dump(value,out,indent=2)
put(control/"fixture-request.json",{"run_id":str(run),"host_hash":host_hash(),"source_identity":snapshot["source_identity"],"fixture_pid":os.getpid(),"fixture_start_ticks":creation+504911232000000000})
deadline=time.monotonic()+15
while not (control/"active.json").exists():
 if time.monotonic()>deadline:raise SystemExit("No active capture: fixture NOT EXECUTED")
 time.sleep(.025) # Control-plane gate BEFORE original fixture; no body-read delay.
active=json.loads((control/"active.json").read_text())
assert active["run_id"]==str(run) and active["profile_sha256"]==bundle["profile_sha256"]
assert kernel.GetTickCount64()+25000<int(active["deadline"]), "Active capture window expired: fixture NOT EXECUTED"
sys.path[:0]=[str(ROOT/"tmp"),str(ROOT),str(ROOT/"apps/backend"),str(ROOT/"apps/backend/tests")]
sys.argv=[sys.argv[0],"d1-native-"+str(run)]
import pr81_http_delivery_observe as d
import pytest


class Plugin(d.Plugin):
 def pytest_collection_finish(self,session):
  super().pytest_collection_finish(session)
  from asyncio.selector_events import _SelectorSocketTransport as Transport
  original=Transport.write
  def write(self,data):
   trace=d.ASGI_TRACE.get()
   if trace is not None and "native_socket" not in trace and self._sock is not None:
    s=self._sock;local=s.getsockname();peer=s.getpeername()
    assert local[0]==peer[0]=="127.0.0.1"
    linger=s.getsockopt(socket.SOL_SOCKET,socket.SO_LINGER,8)
    enabled,seconds=struct.unpack("HH",linger[:4])
    trace["native_socket"]={"family":int(s.family),"type":int(s.type),"python_protocol_requested":s.proto,"native_protocol_info":accepted_protocol(s),"server_port":local[1],"client_port":peer[1],"tcp_nodelay":s.getsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY),"linger_enabled":enabled,"linger_seconds":seconds,"fixture_pid":os.getpid(),"epoch_ns":time.time_ns(),"monotonic_ns":time.monotonic_ns()}
   return original(self,data)
  Transport.write=write
os.chdir(ROOT/"apps/backend")
result=pytest.main(["tests/test_phase13_demo_scripts.py::test_http_seeder_runs_twice_against_one_live_memory_backend","-q","-p","no:cacheprovider","--tb=short"],plugins=[Plugin()])
verify()
traces=[d.describe(t) for t in d.TRACES]
accounting=True
if result==0:
 accounting=len(traces)==10 and all(t["asgi_final_send_returned"] and t["asgi_body_bytes"]==int(t["asgi_framing"]["content-length"])==t["client_socket_received"]["body_bytes"] and t["asgi_body_sha256"]==t["client_socket_received"]["body_sha256"] for t in traces)
final_code=result if result else (0 if accounting else 1)
receipt=ROOT/f"tmp/pr81-tcp-native-{run}.json"
put(receipt,{"run_id":str(run),"source_identity":snapshot["source_identity"],"original_pytest_exit":result,"diagnostic_accounting":accounting,"exit_code":final_code,"traces":traces,"original_deadlines":[15,10],"original_read_amount":1048577,"no_replay":True,"limits":"Native ETW raw file is operator-only; this receipt has ASGI/client safe counts/fingerprints/options, no bodies."})
candidates=[t for t in traces if t.get("native_socket") and (t.get("client_read_outcome")!="RETURN" or t["client_socket_received"]["body_bytes"]<t["asgi_body_bytes"])]
if not candidates:candidates=[t for t in traces if t.get("native_socket")]
if not candidates:
 put(control/"fixture-done.json",{"run_id":str(run),"source_identity":snapshot["source_identity"],"exit_code":final_code,"no_target":True})
else:
 target=candidates[0]
 put(control/"fixture-done.json",{"run_id":str(run),"source_identity":snapshot["source_identity"],"fixture_pid":os.getpid(),"server_port":target["native_socket"]["server_port"],"client_port":target["native_socket"]["client_port"],"correlation":target["correlation"],"exit_code":final_code,"receipt_sha256":hashlib.sha256(receipt.read_bytes()).hexdigest()})
print(json.dumps({"run_id":str(run),"exit_code":final_code,"confirmations":len(traces),"source_preserved":True,"receipt":str(receipt)}))
raise SystemExit(final_code)

