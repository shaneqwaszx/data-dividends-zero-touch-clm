param([string]$OutputPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not ('PR81TcpV5.Native' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'NativeTcp.cs')}
. (Join-Path $PSScriptRoot 'ControllerDiagnostics.ps1')
function Require($condition,[string]$code){if(!$condition){throw $code}}
if(-not ('PR81V5AdverseGetter' -as [type])){Add-Type -TypeDefinition 'public sealed class PR81V5AdverseGetter {public bool HasExited {get {throw new System.Runtime.InteropServices.COMException("",unchecked((int)0x80004005));}}}'}
function Check($ok,[string]$code){if(!$ok){throw ('V5_ADVERSE_'+$code)}}
$rows=[Collections.Generic.List[object]]::new()
foreach($site in @(24,7,25)){
 foreach($conditionId in 1..13){
  $d=[PR81TcpV5.Diagnostic]::new();if($conditionId -eq 13){$null=[PR81TcpV5.WatchdogSafety]::Value($d,$false,$true,$true,$true)};$id=[Guid]::NewGuid();$handle=[uint64]123
  $state=@{start_count=$(if($site -eq 24){0}else{1});enable_count=$(if($site -eq 25){1}else{0});stop_count=0;absence_count=0;failed=$false;export_eligible=$false}
  $owned=$site -ne 24;$stop=$null;$after=$null;$unassociated=$null
  $persist={Write-SafeDiagnostic $d {param($record);if($conditionId -eq 12){throw [Runtime.InteropServices.COMException]::new('',-2147024891)}}}
  try{
   Invoke-CheckedWatchdog $d 45000 {1000} {
    switch($conditionId){
     1{[PR81TcpV5.WatchdogSafety]::Value($d,$false,$true,$true,$true)}
     2{[PR81TcpV5.WatchdogSafety]::Value($d,$true,$true,$true,$true)}
     3{[PR81TcpV5.WatchdogSafety]::Value($d,$null,$true,$true,$true)}
     4{[PR81TcpV5.WatchdogSafety]::Value($d,0,$true,$true,$true)}
     5{[PR81TcpV5.WatchdogSafety]::Value($d,'false',$true,$true,$true)}
     6{
      $scriptProperty=[pscustomobject]@{}
      $scriptProperty|Add-Member ScriptProperty HasExited {throw [Runtime.InteropServices.COMException]::new('',-2147467259)}
      $value=$scriptProperty.PSObject.Properties['HasExited'].GetterScript.InvokeReturnAsIs()
      [PR81TcpV5.WatchdogSafety]::Value($d,$value,$true,$true,$true)
     }
     7{
      $clr=[PR81V5AdverseGetter]::new()
      $value=$clr.get_HasExited()
      [PR81TcpV5.WatchdogSafety]::Value($d,$value,$true,$true,$true)
     }
     8{
      $unassociated=[Diagnostics.Process]::new()
      [PR81TcpV5.WatchdogSafety]::Observe($unassociated,$null,$d)
     }
     9{[PR81TcpV5.WatchdogSafety]::Value($d,$false,$false,$false,$false)}
     10{[PR81TcpV5.WatchdogSafety]::Value($d,$false,$true,$false,$true)}
     11{[PR81TcpV5.WatchdogSafety]::Value($d,$false,$true,$true,$false)}
     12{[PR81TcpV5.WatchdogSafety]::Value($d,$null,$true,$true,$true)}
    }
   } $persist $site
   if($site -eq 24){$state.start_count++;$owned=$true}
   if($site -ne 25){$state.enable_count++}
  }catch{$state.failed=$true;Set-DiagnosticAbort $d $_;& $persist}
  finally{
   if($null -ne $unassociated){$unassociated.Dispose()}
   if($owned){
    $stop=Invoke-ObservedOwnedStop $d $id $handle {
     param($boundId,$boundHandle)
     Check ($boundId -eq $id -and $boundHandle -eq $handle) 'EXACT_STOP'
     $state.stop_count++
     $s=[PR81TcpV5.Stats]::new();$s.BufferSize=64
     $r=[PR81TcpV5.Result]::new();$r.Code=0;$r.DisableAttempted=$true;$r.Stats=$s;$r
    }
   }
  }
  if($owned){
   $after=Invoke-ObservedAbsence $d $id {param($boundId);Check ($boundId -eq $id) 'EXACT_ABSENCE';$state.absence_count++;$r=[PR81TcpV5.Result]::new();$r.Code=4201;$r}
   $snapshot=[PR81TcpV5.Result]::new()
   try{Assert-CaptureExport $state.failed $false $stop $after $snapshot {$true};$state.export_eligible=$true}catch{}
   Check ($state.stop_count -eq 1 -and $state.absence_count -eq 1) 'OWNED_CLEANUP'
  }else{Check ($state.stop_count -eq 0) 'NO_UNCREATED_STOP'}
  if($conditionId -eq 1){Check (!$state.failed -and $state.export_eligible) 'HEALTHY'}
  else{
   Check ($state.failed -and !$state.export_eligible -and $d.WatchdogGuard -eq $false) 'FAIL_CLOSED'
   Check ($d.FailureAttempt -eq $site) 'INITIATING_SITE'
   if($site -eq 24){Check ($state.start_count -eq 0 -and $state.enable_count -eq 0) 'READINESS_PREVENTS_START'}
   if($site -eq 7){Check ($state.enable_count -eq 0) 'PRE_ENABLE_STOPS_ENABLE'}
   if($conditionId -in @(6,7)){Check ($d.WatchdogHResult -eq -2147467259 -and $d.FailureCategory -eq 2) 'GETTER_HRESULT'}
   if($conditionId -eq 8){Check ($d.WatchdogHResult -eq -2146233079) 'REAL_PROCESS_UNASSOCIATED'}
   if($conditionId -eq 12){Check ($d.DiagnosticWriteFailed -and $d.DiagnosticWriteHResult -eq -2147024891) 'WRITE_FAILURE_NO_BYPASS'}
  }
  $record=Get-DiagnosticRecord $d
  Check (Test-Json -Json ($record|ConvertTo-Json -Compress) -SchemaFile (Join-Path $PSScriptRoot 'DIAGNOSTIC_OUTPUT_SCHEMA.json')) 'SAFE_SCHEMA'
  $rows.Add(@{site=$site;condition_id=$conditionId;pass=$true;start_count=$state.start_count;enable_count=$state.enable_count;export_eligible=$state.export_eligible;diagnostic=$record})
 }
}
# Actual process observation only: current test process and an unassociated object; neither is started.
$current=[Diagnostics.Process]::GetCurrentProcess();$samePidOtherObject=[Diagnostics.Process]::GetCurrentProcess();$empty=[Diagnostics.Process]::new()
try{
 $d=[PR81TcpV5.Diagnostic]::new();$bound=[PR81TcpV5.WatchdogSafety]::Bind($current,$d)
 Check ($null -ne $bound -and $d.WatchdogBindingEstablished) 'BIND_ASSOCIATED'
 Check ([PR81TcpV5.WatchdogSafety]::Observe($current,$bound,$d)) 'REAL_ASSOCIATED_HEALTHY'
 Check (![PR81TcpV5.WatchdogSafety]::Observe($samePidOtherObject,$bound,$d) -and !$d.WatchdogIdentityMatch) 'WRONG_ASSOCIATED_OBJECT'
 Check (![PR81TcpV5.WatchdogSafety]::Observe($null,$bound,$d) -and !$d.WatchdogObjectExists) 'ACTUAL_NULL'
 Check ($null -eq [PR81TcpV5.WatchdogSafety]::Bind($empty,$d) -and $d.WatchdogHResult -eq -2146233079) 'BIND_UNASSOCIATED'
 $caught=$null
 try{$null=$empty.get_HasExited()}catch{$caught=Get-NumericHResult $_}
 Check ($caught -eq -2146233079) 'ACTUAL_GETTER_THROW'
}finally{$current.Dispose();$samePidOtherObject.Dispose();$empty.Dispose()}
# Inspect actual controller wiring: no unguarded watchdog property access and every required site is wired.
$controller=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Invoke-Pr81TcpCapture.ps1'))
Check (!$controller.Contains('$watch.HasExited')) 'NO_SWALLOWING_WATCHDOG_ACCESS'
foreach($required in @('WatchdogSafety]::Bind($watch,$d)','{} 24','{} 25','Invoke-ObservedPreEnable $d')){
 Check ($controller.Contains($required)) 'CONTROLLER_SITE_WIRING'
}
$result=@{schema_version=5;synthetic=$true;native_trace_control_invoked=$false;fixture_executed=$false;site_cases=$rows.Count;actual_process_checks=6;cases=$rows}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))}
Write-Output ('V5 watchdog safety PASS: '+$rows.Count+' site/adverse cases + 6 actual process checks; no process started/ETW/fixture')
