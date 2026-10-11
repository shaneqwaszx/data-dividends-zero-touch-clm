param([string]$OutputPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not ('PR81TcpV61.Native' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'NativeTcp.cs')}
. (Join-Path $PSScriptRoot 'ControllerDiagnostics.ps1')
Add-Type -TypeDefinition 'public sealed class PR81V61SyntheticThrowingWatch {public bool HasExited {get {throw new System.Runtime.InteropServices.COMException("",unchecked((int)0x80004005));}}}'
function Require($condition,[string]$code){if(!$condition){throw $code}}
function Check($condition,[string]$name){if(!$condition){$state.failures.Add($name)}}
$cases=[Collections.Generic.List[object]]::new()
foreach($caseId in 1..30){
 $id=[Guid]::NewGuid();$d=[PR81TcpV61.Diagnostic]::new();$d.End(4)
 $s=[PR81TcpV61.Stats]::new();$w=[PR81TcpV61.Wnode]::new();$w.Guid=$id;$s.Wnode=$w
 $s.BufferSize=64;$s.MinimumBuffers=4;$s.MaximumBuffers=16;$s.MaximumFileSize=8;$s.NumberOfBuffers=4;$s.LogFileMode=[PR81TcpV61.Native]::ApprovedLogFileMode
 $fields=@('BufferSize','MinimumBuffers','MaximumBuffers','MaximumFileSize','NumberOfBuffers','LogFileMode','EnableFlags')
 $bad=@(128,8,32,16,17,2,1)
 if($caseId -eq 1){$w.Guid=[Guid]::NewGuid();$s.Wnode=$w}
 if($caseId -ge 2 -and $caseId -le 8){$s.($fields[$caseId-2])=$bad[$caseId-2]}
 $q=[PR81TcpV61.Result]::new();$q.Code=0;$q.Stats=$s
 if($caseId -eq 19){$q.Code=87}
 $watch=[pscustomobject]@{HasExited=($caseId -eq 9)}
 if($caseId -eq 10){$watch=[pscustomobject]@{};$watch|Add-Member ScriptProperty HasExited {throw [Runtime.InteropServices.COMException]::new('',-2147467259)}}
 if($caseId -eq 26){$watch=$null}
 if($caseId -eq 30){$watch=[PR81V61SyntheticThrowingWatch]::new()}
 $inject=switch($caseId){11{8}12{9}13{10}14{11}15{12}16{13}default{0}}
 $returnCode=if($caseId -eq 18){5}else{0}
 $status=[ordered]@{limits_query=$null;enable=$null}
 $state=@{failures=[Collections.Generic.List[string]]::new();stop_count=0;absence_count=0;failed=$false;cleanup_failed=$false;export_eligible=$false;sink_count=0}
 $stop=$null;$after=$null
 $persist={
  Write-SafeDiagnostic $d {
   param($record)
   $state.sink_count++
   if($caseId -in @(23,24)){throw [Runtime.InteropServices.COMException]::new('',-2147024891)}
   foreach($value in $record.Values){Check ($null -eq $value -or $value -is [bool] -or $value -is [int] -or $value -is [uint32] -or $value -is [long] -or $value -is [uint64]) 'SAFE_PRIMITIVE'}
  }
 }
 if($caseId -eq 23){$w.Guid=[Guid]::NewGuid();$s.Wnode=$w;$q.Stats=$s}
 if($caseId -eq 27){$s.NumberOfBuffers=16;$q.Stats=$s}
 try{
  Invoke-ObservedPreEnable $d $id $watch 45000 $status {
   if($caseId -eq 20){throw [Runtime.InteropServices.COMException]::new('',-2147467259)};$q
  } {1000} {
   [PR81TcpV61.Native]::TestEnable($d,$inject,[uint32]$returnCode)
  } {
   param($code)
   if($caseId -eq 17){throw [Runtime.InteropServices.COMException]::new('',-2147467259)}
   $status.enable=$code
  } $persist {
   $value=$null
   if($null -ne $watch){
    $property=$watch.PSObject.Properties['HasExited']
    if($property -is [Management.Automation.PSScriptProperty]){$value=$property.GetterScript.InvokeReturnAsIs()}
    elseif($watch -is [PR81V61SyntheticThrowingWatch]){$value=$watch.get_HasExited()}
    else{$value=$watch.HasExited}
   }
   [PR81TcpV61.WatchdogSafety]::Value($d,$value,($null -ne $watch),($null -ne $watch),($null -ne $watch))
  }
 }catch{$state.failed=$true;Set-DiagnosticAbort $d $_;& $persist}
 finally{
  try{
   $stop=Invoke-ObservedOwnedStop $d $id 123 {
    param($ownedId,$ownedHandle)
    $state.stop_count++;Check ($ownedId -eq $id -and $ownedHandle -eq 123) 'EXACT_STOP_BINDING'
    if($caseId -eq 21){throw [Runtime.InteropServices.COMException]::new('',-2147467259)}
    $r=[PR81TcpV61.Result]::new();$r.Code=0;$r.DisableAttempted=$true;$r.DisableCode=0;$r.Stats=$s
    if($caseId -eq 28){$r.DisableCode=1168}
    $r
   }
  }catch{$state.cleanup_failed=$true}
 }
 try{
  $after=Invoke-ObservedAbsence $d $id {
   param($ownedId)
   $state.absence_count++;Check ($ownedId -eq $id) 'EXACT_QUERY_BINDING'
   if($caseId -eq 22){throw [Runtime.InteropServices.COMException]::new('',-2147467259)}
   $r=[PR81TcpV61.Result]::new();$r.Code=4201;$r
  }
 }catch{$state.cleanup_failed=$true}
 $snapshot=[PR81TcpV61.Result]::new();$snapshot.Code=0
 $d.CaptureFailed=$state.failed;$d.CleanupFailed=$state.cleanup_failed
 try{
  Assert-CaptureExport $state.failed $state.cleanup_failed $stop $after $snapshot { $caseId -ne 29 }
  $state.export_eligible=$true
 }catch{}
 Check ($state.stop_count -eq 1 -and $state.absence_count -eq 1) 'CLEANUP_ALWAYS'
 if($caseId -in @(24,25,27)){Check ($state.export_eligible -and !$d.Aborted) 'SUCCESS_UNCHANGED'}
 else{Check (!$state.export_eligible) 'NO_FALSE_EXPORT'}
 if($caseId -le 8){
  Check ($d.FailureAttempt -eq 6 -and $d.FailedComparisons -eq (1 -shl ($caseId-1))) 'DISTINCT_BOUNDS'
 }
 if($caseId -eq 9){Check ($d.FailureAttempt -eq 7 -and !$d.WatchdogAlive -and $d.FailureCategory -eq 1) 'WATCHDOG_DEAD'}
 if($caseId -eq 10){Check ($d.FailureAttempt -eq 7 -and $d.WatchdogHResult -eq -2147467259 -and $d.FailureCategory -eq 2) 'WATCHDOG_PROPERTY'}
 if($caseId -ge 11 -and $caseId -le 16){Check ($d.FailureAttempt -eq $inject) 'DISTINCT_WRAPPER_STAGE'}
 if($caseId -eq 17){Check ($d.FailureAttempt -eq 15 -and $d.NativeReturned -and $d.NativeReturnCode -eq 0 -and !$d.ControllerAssigned) 'ASSIGNMENT'}
 if($caseId -eq 18){Check ($d.FailureAttempt -eq 16 -and $d.ControllerReturnCode -eq 5) 'NATIVE_ERROR'}
 if($caseId -eq 19){Check ($d.QueryCode -eq 87 -and $d.FailedComparisons -eq 0 -and $d.FailureAttempt -eq 6) 'QUERY_STATUS'}
 if($caseId -eq 20){Check ($d.FailureAttempt -eq 5 -and $null -eq $d.QueryCode) 'QUERY_EXCEPTION'}
 if($caseId -eq 21){Check ($d.CleanupHResult -eq -2147467259 -and $state.cleanup_failed -and $d.FailureAttempt -eq 20 -and $d.FailureCategory -eq 8) 'STOP_EXCEPTION'}
 if($caseId -eq 22){Check ($d.AbsenceHResult -eq -2147467259 -and $state.cleanup_failed -and $d.FailureAttempt -eq 21 -and $d.FailureCategory -eq 8 -and $null -eq $d.Absent) 'ABSENCE_EXCEPTION'}
 if($caseId -in @(23,24)){Check ($d.DiagnosticWriteFailed -and $d.DiagnosticWriteHResult -eq -2147024891) 'DIAGNOSTIC_FAILURE'}
 if($caseId -eq 23){Check ($d.FailureAttempt -eq 6 -and $d.FailureCategory -eq 1 -and $d.FailedComparisons -eq 1) 'ORIGINAL_FAILURE_RETAINED'}
 if($caseId -eq 26){Check (!$d.WatchdogObjectExists -and $d.FailureAttempt -eq 7 -and $null -eq $d.WatchdogAlive) 'NULL_WATCHDOG'}
 if($caseId -eq 28){Check ($d.DisableCode -eq 1168 -and $d.Absent) 'DISABLE_ERROR_NO_EXPORT'}
 if($caseId -ge 11 -and $caseId -le 17){Check ($null -ne $d.ExceptionHResult) 'HRESULT_RECORDED'}
 if($caseId -in @(15,16)){Check ($d.NativeAttempted -and !$d.ControllerAssigned) 'ATTEMPT_NOT_RETURN'}
 Check ($d.LastCompleted -eq $(if($caseId -eq 22){20}else{21})) 'CLEANUP_DOES_NOT_REPLACE_FAILURE'
 if($caseId -eq 30){Check (!$d.WatchdogValueKnown -and !$state.export_eligible) 'CLR_GETTER_UNKNOWN_FAIL_CLOSED'}
 $record=Get-DiagnosticRecord $d
 $json=$record|ConvertTo-Json -Compress
 Check (Test-Json -Json $json -SchemaFile (Join-Path $PSScriptRoot 'DIAGNOSTIC_OUTPUT_SCHEMA.json')) 'EXACT_SCHEMA'
 $cases.Add([ordered]@{case_id=$caseId;pass=($state.failures.Count -eq 0);failed_assertions=@($state.failures);export_eligible=$state.export_eligible;stop_count=$state.stop_count;absence_count=$state.absence_count;diagnostic=$record})
}
$state=@{failures=[Collections.Generic.List[string]]::new()}
# Real bounded safe-file writer, not ETL: temporary file outside repository, no fixture/native control.
$testPath=Join-Path ([IO.Path]::GetTempPath()) ('pr81-v5-diag-test-'+[Guid]::NewGuid().ToString()+'.json')
try{
 $d=[PR81TcpV61.Diagnostic]::new();Save-ControlDiagnostic $d $testPath
 Check (!$d.DiagnosticWriteFailed -and (Test-Path -LiteralPath $testPath)) 'FILE_WRITE'
 $original=[IO.File]::ReadAllText($testPath)
 Save-ControlDiagnostic $d $testPath
 Check ($d.DiagnosticWriteFailed -and [IO.File]::ReadAllText($testPath) -ceq $original) 'NO_OVERWRITE'
 Check ((Get-Item -LiteralPath $testPath).Length -le 16384) 'BOUNDED_WRITE'
 Check (Test-Json -Json ([IO.File]::ReadAllText($testPath)) -SchemaFile (Join-Path $PSScriptRoot 'DIAGNOSTIC_OUTPUT_SCHEMA.json')) 'FILE_SCHEMA'
}finally{if(Test-Path -LiteralPath $testPath){Remove-Item -LiteralPath $testPath}}
$result=[ordered]@{schema_version=5;synthetic=$true;native_trace_control_invoked=$false;fixture_executed=$false;case_count=$cases.Count;failed_cases=@($cases|Where-Object {!$_.pass}).Count;writer_pass=($state.failures.Count -eq 0);writer_failed_assertions=@($state.failures);cases=$cases}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))}
Write-Output ('V6 synthetic diagnostics: '+$cases.Count+' cases; failures='+$result.failed_cases+'; bounded numeric writer; no ETW/fixture')
if($result.failed_cases -gt 0 -or !$result.writer_pass){throw 'V5_SYNTHETIC_CRITERIA_FAILED'}
