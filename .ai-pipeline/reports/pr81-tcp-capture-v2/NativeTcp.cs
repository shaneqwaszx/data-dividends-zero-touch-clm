using System;
using System.Runtime.InteropServices;
namespace PR81TcpV2 {
 [StructLayout(LayoutKind.Sequential)] public struct Wnode {
  public uint BufferSize,ProviderId; public ulong HistoricalContext,TimeStamp;
  public Guid Guid; public uint ClientContext,Flags;
 }
 [StructLayout(LayoutKind.Sequential)] public struct Stats {
  public Wnode Wnode; public uint BufferSize,MinimumBuffers,MaximumBuffers,MaximumFileSize,LogFileMode,FlushTimer,EnableFlags;
  public int AgeLimit; public uint NumberOfBuffers,FreeBuffers,EventsLost,BuffersWritten,LogBuffersLost,RealTimeBuffersLost;
  public IntPtr LoggerThreadId; public uint LogFileNameOffset,LoggerNameOffset;
 }
 [StructLayout(LayoutKind.Sequential)] struct Filter {public ulong Ptr;public uint Size,Type;}
 [StructLayout(LayoutKind.Sequential)] struct Enable {public uint Version,EnableProperty,ControlFlags;public Guid SourceId;public IntPtr Filters;public uint Count;}
 public sealed class Result {public uint Code;public Stats Stats;public ulong Handle;public bool DisableAttempted;public uint DisableCode;}
 public static class Native {
  [DllImport("kernel32.dll")] static extern ulong GetTickCount64();
  public static long Clock(){return checked((long)GetTickCount64());}
  public const string Name="PR81-Loopback-TCP-Metadata";
  static Guid Provider=new Guid("2f07e2ee-15db-40f1-90ef-9d7ba282188a");
  static ushort[] Ids={1002,1017,1033,1038,1043,1051,1071,1073,1074,1077,1176,1180,1184,1300,1330,1332,1351,1449,1479,1637};
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode)] static extern uint StartTraceW(out ulong h,string name,IntPtr p);
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode)] static extern uint ControlTraceW(ulong h,string name,IntPtr p,uint code);
  [DllImport("advapi32.dll")] static extern uint EnableTraceEx2(ulong h,ref Guid provider,uint control,byte level,ulong any,ulong all,uint timeout,ref Enable p);
  static IntPtr Props(Guid id,string file,bool start) {
   if(file.Length>=1023)throw new ArgumentException("Path length");
   int size=Marshal.SizeOf(typeof(Stats)); int total=size+4096;
   IntPtr ptr=Marshal.AllocHGlobal(total);Marshal.Copy(new byte[total],0,ptr,total);
   Stats p=new Stats();p.Wnode.BufferSize=(uint)total;p.Wnode.Guid=id;p.Wnode.Flags=0x20000;
   p.LoggerNameOffset=(uint)size;p.LogFileNameOffset=(uint)(size+2048);
   if(start){p.Wnode.ClientContext=1;p.BufferSize=64;p.MinimumBuffers=4;p.MaximumBuffers=16;p.MaximumFileSize=8;p.LogFileMode=0x10000002;p.FlushTimer=1;}
   Marshal.StructureToPtr(p,ptr,false);
   if(start){if(file.Length>=1023)throw new ArgumentException("Path length");Marshal.Copy((file+"\0").ToCharArray(),0,IntPtr.Add(ptr,size+2048),file.Length+1);}
   return ptr;
  }
  public static bool Owned(Stats p,Guid id){return p.Wnode.Guid==id&&id!=Guid.Empty;}
  public static bool Bounds(Stats p){return p.BufferSize==64&&p.MinimumBuffers==4&&p.MaximumBuffers==16&&p.MaximumFileSize==8&&p.NumberOfBuffers<=16&&p.LogFileMode==0x10000002&&p.EnableFlags==0;}
  public static bool Complete(Stats p){return p.EventsLost==0&&p.LogBuffersLost==0&&p.RealTimeBuffersLost==0&&((ulong)p.BuffersWritten+1)*p.BufferSize*1024<8*1024*1024;}
  public static Result Query(Guid id) {return QueryHandle(id,0);}
  static Result QueryHandle(Guid id,ulong handle) {
   IntPtr ptr=Props(id,"",false);try{uint code=ControlTraceW(handle,handle==0?Name:null,ptr,0);return new Result{Code=code,Stats=(Stats)Marshal.PtrToStructure(ptr,typeof(Stats))};}finally{Marshal.FreeHGlobal(ptr);}
  }
  public static Result Start(Guid id,string file) {
   if(id==Guid.Empty)throw new ArgumentException("Empty run");
   IntPtr ptr=Props(id,file,true);try{ulong h;uint code=StartTraceW(out h,Name,ptr);return new Result{Code=code,Handle=h,Stats=(Stats)Marshal.PtrToStructure(ptr,typeof(Stats))};}finally{Marshal.FreeHGlobal(ptr);}
  }
  public static uint EnableOnly(ulong h,Guid id) {
   IntPtr data=Marshal.AllocHGlobal(4+2*Ids.Length);IntPtr desc=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Filter)));
   try{
    Marshal.Copy(new byte[4+2*Ids.Length],0,data,4+2*Ids.Length);Marshal.WriteByte(data,0,1);Marshal.WriteInt16(data,2,(short)Ids.Length);
    for(int i=0;i<Ids.Length;i++)Marshal.WriteInt16(data,4+2*i,(short)Ids[i]);
    Marshal.StructureToPtr(new Filter{Ptr=unchecked((ulong)data.ToInt64()),Size=(uint)(4+2*Ids.Length),Type=0x80000200},desc,false);
    Enable ep=new Enable{Version=2,SourceId=id,Filters=desc,Count=1};
    return EnableTraceEx2(h,ref Provider,1,5,0x0000409700000486,0,1000,ref ep);
   }finally{Marshal.FreeHGlobal(data);Marshal.FreeHGlobal(desc);}
  }
  public static uint Disable(ulong h,Guid id) {Enable ep=new Enable{Version=2,SourceId=id};return EnableTraceEx2(h,ref Provider,0,0,0,0,1000,ref ep);}
  public static Result Stop(Guid id,ulong handle) {
   Result current=Query(id);if(current.Code==4201)return current;
   if(current.Code!=0||!Owned(current.Stats,id))return new Result{Code=current.Code!=0?current.Code:87};
   ulong selected=handle!=0?handle:current.Stats.Wnode.HistoricalContext;
   if(selected==0)return new Result{Code=87};
   Result bound=QueryHandle(id,selected);
   if(bound.Code!=0||!Owned(bound.Stats,id))return new Result{Code=bound.Code!=0?bound.Code:87};
   uint disableCode=Disable(selected,id);
   IntPtr ptr=Props(id,"",false);try{uint code=ControlTraceW(selected,null,ptr,1);return new Result{Code=code,Stats=(Stats)Marshal.PtrToStructure(ptr,typeof(Stats)),DisableAttempted=true,DisableCode=disableCode};}finally{Marshal.FreeHGlobal(ptr);}
  }
  public static int StatsSize(){return Marshal.SizeOf(typeof(Stats));}
  public static int EnableSize(){return Marshal.SizeOf(typeof(Enable));}
 }
}
