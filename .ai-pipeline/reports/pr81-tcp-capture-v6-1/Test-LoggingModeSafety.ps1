param([string]$OutputPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not ('PR81TcpV61.Native' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'NativeTcp.cs')}
. (Join-Path $PSScriptRoot 'ControllerDiagnostics.ps1')
function Require($condition,[string]$code){if(!$condition){throw $code}}
$rows=[Collections.Generic.List[object]]::new()
function Check($condition,[string]$code){if(!$condition){throw ('V6_MODE_TEST_'+$code)}}
function GoodStats([Guid]$id){
 $s=[PR81TcpV61.Stats]::new();$w=[PR81TcpV61.Wnode]::new();$w.Guid=$id;$s.Wnode=$w
 $s.BufferSize=64;$s.MinimumBuffers=4;$s.MaximumBuffers=16;$s.MaximumFileSize=8
 $s.NumberOfBuffers=4;$s.LogFileMode=0x10400002;return $s
}
$modes=@(
 @{name='approved';value=[uint32]0x10400002;pass=$true},
 @{name='missing_stop_v5';value=[uint32]0x10000002;pass=$false},
 @{name='extra_realtime';value=[uint32]0x10400102;pass=$false},
 @{name='persist_substitutes_stop';value=[uint32]0x10800002;pass=$false},
 @{name='stop_and_persist';value=[uint32]0x10c00002;pass=$false},
 @{name='missing_circular';value=[uint32]0x10400000;pass=$false},
 @{name='missing_shared_buffers';value=[uint32]0x00400002;pass=$false},
 @{name='zero';value=[uint32]0;pass=$false},
 @{name='circular_only';value=[uint32]2;pass=$false},
 @{name='all_bits';value=[uint32]::MaxValue;pass=$false}
)
# Each of the 29 absent bits must individually reject; includes PERSIST and all unknown bits.
foreach($bit in 0..31){
 $extra=[uint32]([uint64]1 -shl $bit)
 if(([uint32]0x10400002 -band $extra) -eq 0){
  $modes+=@{name=('unexpected_bit_'+$bit);value=([uint32]0x10400002 -bor $extra);pass=$false}
 }
}
foreach($case in $modes){
 $id=[Guid]::NewGuid();$s=GoodStats $id;$s.LogFileMode=$case.value
 Check ([PR81TcpV61.Native]::Bounds($s) -eq $case.pass) 'NATIVE_EXACT_EQUALITY'
 $d=[PR81TcpV61.Diagnostic]::new();$q=[PR81TcpV61.Result]::new();$q.Code=0;$q.Stats=$s
 $status=@{limits_query=$null;enable=$null};$state=@{enable=0;stop=0;absence=0;failed=$false}
 $handle=[uint64]123
 try{
  Invoke-ObservedPreEnable $d $id $null 45000 $status {$q} {1000} {
   $state.enable++;[PR81TcpV61.Native]::TestEnable($d,0,0)
  } {param($code);$status.enable=$code} {} {
   [PR81TcpV61.WatchdogSafety]::Value($d,$false,$true,$true,$true)
  }
 }catch{$state.failed=$true;Set-DiagnosticAbort $d $_}
 finally{
  $stop=Invoke-ObservedOwnedStop $d $id $handle {
   param($ownedId,$ownedHandle)
   Check ($ownedId -eq $id -and $ownedHandle -eq $handle) 'EXACT_STOP_BINDING'
   $state.stop++;$result=[PR81TcpV61.Result]::new();$result.Code=0;$result.DisableAttempted=$true;$result
  }
 }
 $after=Invoke-ObservedAbsence $d $id {
  param($ownedId);Check ($ownedId -eq $id) 'EXACT_ABSENCE_BINDING'
  $state.absence++;$result=[PR81TcpV61.Result]::new();$result.Code=4201;$result
 }
 Check ($state.stop -eq 1 -and $state.absence -eq 1 -and $d.Absent) 'CLEANUP_ALWAYS'
 Check ($state.failed -eq !$case.pass -and $state.enable -eq [int]$case.pass) 'PRE_ENABLE_GATE'
 if(!$case.pass){Check ($d.FailedComparisons -eq 64 -and $d.FailureAttempt -eq 6 -and !$d.WrapperEntered) 'SOLE_MODE_MASK'}
 else{Check ($d.FailedComparisons -eq 0 -and $d.ControllerAssigned) 'POSITIVE_CONTROL'}
 $rows.Add(@{name=$case.name;mode=$case.value;approved=$case.pass;pass=$true})
}
foreach($pair in @(
 @('BufferSize',128),@('MinimumBuffers',8),@('MaximumBuffers',32),
 @('MaximumFileSize',16),@('NumberOfBuffers',17),@('EnableFlags',1)
)){
 $s=GoodStats ([Guid]::NewGuid());$s.($pair[0])=$pair[1]
 Check (![PR81TcpV61.Native]::Bounds($s)) ('UNCHANGED_BOUND_'+$pair[0])
 $rows.Add(@{name=('bound_'+$pair[0]);pass=$true})
}
$id=[Guid]::NewGuid();$s=GoodStats $id
Check ([PR81TcpV61.Native]::Owned($s,$id)) 'EXACT_GUID'
Check (![PR81TcpV61.Native]::Owned($s,[Guid]::NewGuid())) 'FOREIGN_GUID'
$empty=GoodStats ([Guid]::Empty)
Check (![PR81TcpV61.Native]::Owned($empty,[Guid]::Empty)) 'EMPTY_GUID'
foreach($name in @('owned_guid','foreign_guid','empty_guid')){$rows.Add(@{name=$name;pass=$true})}
# Reflect the same private Props used by StartTrace, marshal and free WITHOUT any native control API.
$flags=[Reflection.BindingFlags]::NonPublic -bor [Reflection.BindingFlags]::Static
$method=[PR81TcpV61.Native].GetMethod('Props',$flags)
$ptr=[IntPtr]::Zero
try{
 $ptr=$method.Invoke($null,[object[]]@($id,'synthetic-not-opened.etl',$true))
 $props=[Runtime.InteropServices.Marshal]::PtrToStructure($ptr,[type][PR81TcpV61.Stats])
 Check ($props.LogFileMode -eq 0x10400002 -and [PR81TcpV61.Native]::ApprovedLogFileMode -eq 0x10400002) 'ACTUAL_START_PROPERTIES'
 Check ($props.BufferSize -eq 64 -and $props.MinimumBuffers -eq 4 -and $props.MaximumBuffers -eq 16 -and $props.MaximumFileSize -eq 8 -and $props.FlushTimer -eq 1 -and $props.Wnode.ClientContext -eq 1 -and $props.EnableFlags -eq 0 -and $props.Wnode.Guid -eq $id) 'START_CONSTRAINTS'
}finally{if($ptr -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)}}
$rows.Add(@{name='actual_start_properties_without_native_call';pass=$true})
$p=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json') -Raw|ConvertFrom-Json
Check ($p.log_file_mode -eq [PR81TcpV61.Native]::ApprovedLogFileMode) 'PROFILE_MODE_BINDING'
Check ($p.capture_duration_seconds -eq 45 -and $p.arming_wait_seconds -eq 300 -and $p.maximum_file_size_mib -eq 8 -and $p.buffer_size_kib -eq 64 -and $p.minimum_buffers -eq 4 -and $p.maximum_buffers -eq 16) 'PROFILE_BOUNDS'
$rows.Add(@{name='profile_mode_and_constraints';pass=$true})
$result=@{helper_version=6;case_count=$rows.Count;failed_cases=0;native_trace_control_invoked=$false;fixture_executed=$false;cases=$rows}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 7),[Text.UTF8Encoding]::new($false))}
Write-Output ('V6 mode safety PASS: '+$rows.Count+' cases; exact mode, all extra bits, unchanged bounds/ownership and actual Start properties; no ETW/fixture')
