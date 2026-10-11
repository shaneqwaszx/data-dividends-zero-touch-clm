using System;
using System.Runtime.InteropServices;
namespace PR81TcpV6 {
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
 public sealed class Diagnostic {
  public int SchemaVersion=5;
  public int LastCompleted=0,CurrentAttempt=0,CurrentCategory=0;
  public ulong CompletedStages=0;
  public bool Aborted=false,DiagnosticWriteFailed=false;
  public int? FailureLastCompleted,FailureAttempt,FailureCategory,ExceptionHResult,DiagnosticWriteHResult,CleanupHResult,AbsenceHResult;
  public uint? QueryCode,BufferSize,MinimumBuffers,MaximumBuffers,MaximumFileSize,NumberOfBuffers,LogFileMode,EnableFlags,FailedComparisons;
  public bool? OwnershipMatch,BufferSizeMatch,MinimumBuffersMatch,MaximumBuffersMatch,MaximumFileSizeMatch,NumberOfBuffersMatch,LogFileModeMatch,EnableFlagsMatch,LimitsGuard;
  public bool? WatchdogObjectExists,WatchdogAlive,WatchdogGuard,WatchdogValueKnown;
  public bool WatchdogEvaluationErrorObserved=false;
  public bool? WatchdogAssociated,WatchdogIdentityMatch,WatchdogBindingEstablished;
  public int WatchdogEvaluationSite=0;
  public int? WatchdogHResult;
  public long? WatchdogTick,DeadlineRemaining;
  public bool WrapperEntered=false,NativeAttempted=false,NativeReturned=false,ControllerAssigned=false;
  public uint? NativeReturnCode,ControllerReturnCode,FailureNativeStatus,StopCode,DisableCode,AbsenceCode;
  public bool? StopAttempted,DisableAttempted,Absent,CaptureFailed,CleanupFailed;
  public void Begin(int stage,int category){CurrentAttempt=stage;CurrentCategory=category;}
  public void End(int stage){LastCompleted=stage;CompletedStages|=1UL<<stage;}
  public void Abort(int? hr) {
   if(Aborted)return;
   Aborted=true;FailureLastCompleted=LastCompleted;FailureAttempt=CurrentAttempt;FailureCategory=CurrentCategory;ExceptionHResult=hr;
   FailureNativeStatus=CurrentAttempt==6?QueryCode:(CurrentAttempt==16?ControllerReturnCode:NativeReturnCode);
  }
 }

 public sealed class WatchdogBinding {
  internal readonly System.Diagnostics.Process Owner;
  internal readonly int ProcessId;
  internal readonly long StartTicks;
  internal WatchdogBinding(System.Diagnostics.Process p,int id,long ticks){Owner=p;ProcessId=id;StartTicks=ticks;}
 }
 public static class WatchdogSafety {
  public static void Reset(Diagnostic d){
   d.WatchdogObjectExists=false;d.WatchdogAssociated=false;d.WatchdogIdentityMatch=false;
   d.WatchdogValueKnown=false;d.WatchdogAlive=null;d.WatchdogGuard=false;
   d.WatchdogEvaluationErrorObserved=false;d.WatchdogHResult=null;
  }
  public static void Error(Diagnostic d,Exception e){
   while(e.InnerException!=null)e=e.InnerException;
   d.WatchdogEvaluationErrorObserved=true;d.WatchdogHResult=e.HResult;d.WatchdogGuard=false;d.WatchdogAlive=null;d.WatchdogValueKnown=false;
  }
  // One owning predicate is shared by actual Process observation and synthetic adverse values.
  public static bool Value(Diagnostic d,object exited,bool exists,bool associated,bool identity){
   d.WatchdogObjectExists=exists;d.WatchdogAssociated=associated;d.WatchdogIdentityMatch=identity;
   d.WatchdogValueKnown=exited is bool;d.WatchdogAlive=exited is bool?(bool?)(!(bool)exited):null;
   d.WatchdogGuard=exists&&associated&&identity&&exited is bool&&!(bool)exited;
   return d.WatchdogGuard==true;
  }
  public static WatchdogBinding Bind(System.Diagnostics.Process p,Diagnostic d){
   Reset(d);d.WatchdogBindingEstablished=false;d.WatchdogObjectExists=p!=null;
   if(p==null)return null;
   try{
    int id=p.Id;long ticks=p.StartTime.ToUniversalTime().Ticks;
    d.WatchdogAssociated=id>0&&ticks>0;
    if(d.WatchdogAssociated!=true)return null;
    d.WatchdogBindingEstablished=true;
    return new WatchdogBinding(p,id,ticks);
   }catch(Exception e){Error(d,e);return null;}
  }
  public static bool Observe(System.Diagnostics.Process p,WatchdogBinding bound,Diagnostic d){
   Reset(d);d.WatchdogObjectExists=p!=null;
   if(p==null)return false;
   try{
    int id=p.Id;long ticks=p.StartTime.ToUniversalTime().Ticks;
    d.WatchdogAssociated=id>0&&ticks>0;
    bool identity=bound!=null&&object.ReferenceEquals(p,bound.Owner)&&id==bound.ProcessId&&ticks==bound.StartTicks;
    d.WatchdogIdentityMatch=identity;
    if(d.WatchdogAssociated!=true||!identity)return false;
    // Typed managed getter: bypass PowerShell's error-swallowing property adapter.
    bool exited=p.HasExited;
    return Value(d,exited,true,true,identity);
   }catch(Exception e){Error(d,e);return false;}
  }
 }

 public static class Native {
  // Windows SDK evntrace.h constants; explicit stop matches the documented default observed in V5.
  public const uint EVENT_TRACE_FILE_MODE_CIRCULAR=0x00000002;
  public const uint EVENT_TRACE_NO_PER_PROCESSOR_BUFFERING=0x10000000;
  public const uint EVENT_TRACE_STOP_ON_HYBRID_SHUTDOWN=0x00400000;
  public const uint ApprovedLogFileMode=EVENT_TRACE_FILE_MODE_CIRCULAR|EVENT_TRACE_NO_PER_PROCESSOR_BUFFERING|EVENT_TRACE_STOP_ON_HYBRID_SHUTDOWN;
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
   if(start){p.Wnode.ClientContext=1;p.BufferSize=64;p.MinimumBuffers=4;p.MaximumBuffers=16;p.MaximumFileSize=8;p.LogFileMode=ApprovedLogFileMode;p.FlushTimer=1;}
   Marshal.StructureToPtr(p,ptr,false);
   if(start){if(file.Length>=1023)throw new ArgumentException("Path length");Marshal.Copy((file+"\0").ToCharArray(),0,IntPtr.Add(ptr,size+2048),file.Length+1);}
   return ptr;
  }
  public static bool Owned(Stats p,Guid id){return p.Wnode.Guid==id&&id!=Guid.Empty;}
  public static bool Bounds(Stats p){return p.BufferSize==64&&p.MinimumBuffers==4&&p.MaximumBuffers==16&&p.MaximumFileSize==8&&p.NumberOfBuffers<=16&&p.LogFileMode==ApprovedLogFileMode&&p.EnableFlags==0;}
  public static bool Complete(Stats p){return p.EventsLost==0&&p.LogBuffersLost==0&&p.RealTimeBuffersLost==0&&((ulong)p.BuffersWritten+1)*p.BufferSize*1024<8*1024*1024;}
  public static Result Query(Guid id) {return QueryHandle(id,0);}
  static Result QueryHandle(Guid id,ulong handle) {
   IntPtr ptr=Props(id,"",false);try{uint code=ControlTraceW(handle,handle==0?Name:null,ptr,0);return new Result{Code=code,Stats=(Stats)Marshal.PtrToStructure(ptr,typeof(Stats))};}finally{Marshal.FreeHGlobal(ptr);}
  }
  public static Result Start(Guid id,string file) {
   if(id==Guid.Empty)throw new ArgumentException("Empty run");
   IntPtr ptr=Props(id,file,true);try{ulong h;uint code=StartTraceW(out h,Name,ptr);return new Result{Code=code,Handle=h,Stats=(Stats)Marshal.PtrToStructure(ptr,typeof(Stats))};}finally{Marshal.FreeHGlobal(ptr);}
  }
  // Runtime path has no injection switch. Tests share this implementation with a fake native return.
  public static uint EnableOnly(ulong h,Guid id,Diagnostic d){return EnableCore(h,id,d,false,0,0);}
  public static uint TestEnable(Diagnostic d,int failureStage,uint returnCode){return EnableCore(0,Guid.NewGuid(),d,true,failureStage,returnCode);}
  static void Hit(bool test,int selected,int current){if(test&&selected==current)throw new System.Runtime.InteropServices.COMException("",unchecked((int)0x80004005));}
  static uint EnableCore(ulong h,Guid id,Diagnostic d,bool test,int failureStage,uint returnCode) {
   d.Begin(8,9);d.WrapperEntered=true;Hit(test,failureStage,8);d.End(8);
   d.Begin(9,3);Hit(test,failureStage,9);IntPtr data=Marshal.AllocHGlobal(4+2*Ids.Length);d.End(9);
   d.Begin(10,3);Hit(test,failureStage,10);IntPtr desc=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Filter)));d.End(10);
   try{
    d.Begin(11,4);Hit(test,failureStage,11);
    Marshal.Copy(new byte[4+2*Ids.Length],0,data,4+2*Ids.Length);Marshal.WriteByte(data,0,1);Marshal.WriteInt16(data,2,(short)Ids.Length);
    for(int i=0;i<Ids.Length;i++)Marshal.WriteInt16(data,4+2*i,(short)Ids[i]);
    Marshal.StructureToPtr(new Filter{Ptr=unchecked((ulong)data.ToInt64()),Size=(uint)(4+2*Ids.Length),Type=0x80000200},desc,false);
    Enable ep=new Enable{Version=2,SourceId=id,Filters=desc,Count=1};d.End(11);
    d.Begin(12,5);d.NativeAttempted=true;Hit(test,failureStage,12);
    uint code=test?returnCode:EnableTraceEx2(h,ref Provider,1,5,0x0000409700000486,0,1000,ref ep);
    d.NativeReturned=true;d.End(12);
    d.Begin(13,6);Hit(test,failureStage,13);d.NativeReturnCode=code;d.End(13);
    return code;
   }finally{
    // Preserve V3 allocation and finally ordering; do not repair its separate allocation-leak hypothesis.
    // Do not replace the initiating stage while unwinding an earlier exception.
    if(d.NativeReturnCode.HasValue)d.Begin(14,8);
    Marshal.FreeHGlobal(data);Marshal.FreeHGlobal(desc);
    if(d.NativeReturnCode.HasValue)d.End(14);
   }
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
