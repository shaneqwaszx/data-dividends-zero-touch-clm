function Invoke-CheckedWatchdog($d,[long]$deadline,[scriptblock]$Clock,[scriptblock]$Probe,[scriptblock]$Persist,[int]$Stage=7){
 $d.Begin($Stage,2);$d.WatchdogEvaluationSite=$Stage
 [PR81TcpV61.WatchdogSafety]::Reset($d)
 $d.WatchdogTick=& $Clock;$d.DeadlineRemaining=$deadline-$d.WatchdogTick
 try{& $Probe|Out-Null}
 catch{
  $d.WatchdogGuard=$false;$d.WatchdogAlive=$null;$d.WatchdogValueKnown=$false
  $d.WatchdogEvaluationErrorObserved=$true;$d.WatchdogHResult=Get-NumericHResult $_
 }
 & $Persist
 $d.CurrentCategory=if($d.WatchdogEvaluationErrorObserved){2}else{1}
 Require ($d.WatchdogGuard -eq $true -and $d.WatchdogObjectExists -eq $true -and $d.WatchdogAssociated -eq $true -and $d.WatchdogIdentityMatch -eq $true -and $d.WatchdogValueKnown -eq $true -and $d.WatchdogAlive -eq $true) 'WATCHDOG_INVALID_OR_NOT_ALIVE'
 $d.End($Stage)
}

# Fixed-field numeric diagnostics. No exception rendering or unrestricted object serialization.
function Get-NumericHResult($errorObject){
 $exception=$errorObject.Exception
 if($null -eq $exception){return $null}
 while($null -ne $exception.InnerException){$exception=$exception.InnerException}
 return [int]$exception.HResult
}
function Get-DiagnosticRecord($d){
 $record=[ordered]@{}
 foreach($field in [PR81TcpV61.Diagnostic].GetFields()){
  $record[$field.Name]=$field.GetValue($d)
 }
 return $record
}
function Write-SafeDiagnostic($d,[scriptblock]$Sink){
 try{& $Sink (Get-DiagnosticRecord $d)|Out-Null}
 catch{$d.DiagnosticWriteFailed=$true;$d.DiagnosticWriteHResult=Get-NumericHResult $_}
}
function Save-ControlDiagnostic($d,[string]$Path){
 Write-SafeDiagnostic $d ({
  param($record)
  $json=$record|ConvertTo-Json -Depth 3 -Compress
  if([Text.Encoding]::UTF8.GetByteCount($json) -gt 16384){throw 'DIAGNOSTIC_SIZE'}
  # At most six fresh fixed-name 16 KiB records. CreateNew rejects reuse; never overwrite/append.
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes($json)
  $stream=[IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
 }.GetNewClosure())
}
function Set-DiagnosticAbort($d,$errorObject){
 $d.Abort((Get-NumericHResult $errorObject))
}
function Invoke-ObservedPreEnable($d,[Guid]$id,$watch,[long]$deadline,$status,
 [scriptblock]$Query,[scriptblock]$Clock,[scriptblock]$Enable,[scriptblock]$Assign,[scriptblock]$Persist,[scriptblock]$WatchdogProbe){
 $d.Begin(5,9)
 $q=& $Query
 $status.limits_query=$q.Code;$d.QueryCode=$q.Code
 $s=$q.Stats
 $d.BufferSize=$s.BufferSize;$d.MinimumBuffers=$s.MinimumBuffers;$d.MaximumBuffers=$s.MaximumBuffers
 $d.MaximumFileSize=$s.MaximumFileSize;$d.NumberOfBuffers=$s.NumberOfBuffers;$d.LogFileMode=$s.LogFileMode;$d.EnableFlags=$s.EnableFlags
 $d.OwnershipMatch=[PR81TcpV61.Native]::Owned($s,$id)
 $d.BufferSizeMatch=$s.BufferSize -eq 64;$d.MinimumBuffersMatch=$s.MinimumBuffers -eq 4
 $d.MaximumBuffersMatch=$s.MaximumBuffers -eq 16;$d.MaximumFileSizeMatch=$s.MaximumFileSize -eq 8
 $d.NumberOfBuffersMatch=$s.NumberOfBuffers -le 16;$d.LogFileModeMatch=$s.LogFileMode -eq [PR81TcpV61.Native]::ApprovedLogFileMode;$d.EnableFlagsMatch=$s.EnableFlags -eq 0
 $mask=[uint32]0;$bit=0
 foreach($ok in @($d.OwnershipMatch,$d.BufferSizeMatch,$d.MinimumBuffersMatch,$d.MaximumBuffersMatch,$d.MaximumFileSizeMatch,$d.NumberOfBuffersMatch,$d.LogFileModeMatch,$d.EnableFlagsMatch)){
  if(!$ok){$mask=$mask -bor (1 -shl $bit)};$bit++
 }
 $d.FailedComparisons=$mask
 # Keep the authoritative V3 aggregate, including native-code success, unchanged.
 $d.LimitsGuard=$q.Code -eq 0 -and [PR81TcpV61.Native]::Owned($s,$id) -and [PR81TcpV61.Native]::Bounds($s)
 $d.End(5);$d.Begin(6,1)
 & $Persist
 Require ($d.LimitsGuard) 'QUERIED_LIMIT_MISMATCH';$d.End(6)
 Invoke-CheckedWatchdog $d $deadline $Clock $WatchdogProbe $Persist 7
 $code=& $Enable
 $d.Begin(15,7)
 & $Assign $code
 $d.ControllerReturnCode=$status.enable;$d.ControllerAssigned=$true;$d.End(15)
 $d.Begin(16,1);Require ($status.enable -eq 0) 'ENABLE_FAILURE';$d.End(16)
 & $Persist
}
function Invoke-ObservedOwnedStop($d,[Guid]$id,[uint64]$handle,[scriptblock]$Stop){
 $d.Begin(20,8);$d.StopAttempted=$true
 try{
  $result=& $Stop $id $handle
  $d.StopCode=$result.Code;$d.DisableAttempted=$result.DisableAttempted
  if($result.DisableAttempted){$d.DisableCode=$result.DisableCode}
  $d.End(20);return $result
 }catch{$d.CleanupHResult=Get-NumericHResult $_;$d.Abort($d.CleanupHResult);throw}
}
function Invoke-ObservedAbsence($d,[Guid]$id,[scriptblock]$Query){
 $d.Begin(21,8)
 try{$after=& $Query $id;$d.AbsenceCode=$after.Code;$d.Absent=$after.Code -eq 4201;$d.End(21);return $after}
 catch{$d.AbsenceHResult=Get-NumericHResult $_;$d.Abort($d.AbsenceHResult);throw}
}
function Assert-CaptureExport($failed,$cleanupFailed,$stop,$after,$snapshot,[scriptblock]$DoneExists){
 Require (!$failed -and !$cleanupFailed -and $null -ne $stop -and $stop.DisableAttempted -and $stop.DisableCode -eq 0) 'CAPTURE_ABORTED_NO_EXPORT'
 Require ($after.Code -eq 4201 -and $stop.Code -eq 0 -and $null -ne $snapshot -and $snapshot.Code -eq 0 -and [PR81TcpV61.Native]::Complete($stop.Stats)) 'INCOMPLETE_OR_CLEANUP_FAILURE'
 Require (& $DoneExists) 'FIXTURE_NOT_DONE_BEFORE_DEADLINE'
}
