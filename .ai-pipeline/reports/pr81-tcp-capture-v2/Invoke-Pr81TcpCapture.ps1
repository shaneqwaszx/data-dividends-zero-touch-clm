param([ValidateSet('Arm','Watchdog','Validate')][string]$Mode='Arm',[Guid]$RunId=[Guid]::Empty,[long]$Deadline=0)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -lt 7){throw 'REQUIRES_INSTALLED_POWERSHELL_7'}
$bundle=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'bundle.json') -Raw|ConvertFrom-Json
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
function Require($condition,[string]$code){if(!$condition){throw $code}}
foreach($file in $bundle.files.PSObject.Properties){Require ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $file.Name)).Hash.ToLower() -eq $file.Value) 'BUNDLE_HASH'}
foreach($file in $bundle.source_hashes.PSObject.Properties){Require ((Get-FileHash -LiteralPath (Join-Path $root $file.Name)).Hash.ToLower() -eq $file.Value) 'SOURCE_HASH'}
Require ([Environment]::Is64BitProcess) 'REQUIRES_X64'
$schema=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../PR81_TCP_TRACE_EVENT_SCHEMA_V2.json') -Raw|ConvertFrom-Json
$p=Get-WinEvent -ListProvider 'Microsoft-Windows-TCPIP'
$current=@($p.Events|Where-Object {$_.Id -in $bundle.event_ids})
Require ($current.Count -eq $schema.Events.Count) 'SCHEMA_VERSION_COUNT'
foreach($expected in $schema.Events){
 $match=@($current|Where-Object {$_.Id -eq $expected.Id -and $_.Version -eq $expected.Version})
 Require ($match.Count -eq 1 -and $match[0].Template -ceq $expected.Template -and $match[0].Level.Value -eq $expected.Level) 'SCHEMA_DRIFT'
}
Add-Type -Path (Join-Path $PSScriptRoot 'NativeTcp.cs')
if($Mode -eq 'Validate'){
 Require ([PR81TcpV2.Native]::StatsSize() -eq 120 -and [PR81TcpV2.Native]::EnableSize() -eq 48) 'NATIVE_LAYOUT'
 $s=[PR81TcpV2.Stats]::new();$id=[Guid]::NewGuid();$w=[PR81TcpV2.Wnode]::new();$w.Guid=$id;$s.Wnode=$w
 Require ([PR81TcpV2.Native]::Owned($s,$id) -and ![PR81TcpV2.Native]::Owned($s,[Guid]::NewGuid())) 'OWNERSHIP_GUARD'
 $s.BufferSize=64;$s.MinimumBuffers=4;$s.MaximumBuffers=16;$s.MaximumFileSize=8;$s.NumberOfBuffers=4;$s.LogFileMode=268435458
 Require ([PR81TcpV2.Native]::Bounds($s)) 'BOUNDS_ACCEPT';$s.MaximumBuffers=32;Require (![PR81TcpV2.Native]::Bounds($s)) 'BOUNDS_REJECT';$s.MaximumBuffers=16
 $s.EventsLost=1;Require (![PR81TcpV2.Native]::Complete($s)) 'LOSS_REJECT';$s.EventsLost=0;$s.BuffersWritten=127;Require (![PR81TcpV2.Native]::Complete($s)) 'OVERWRITE_REJECT'
 & (Join-Path $PSScriptRoot 'Sanitize-TcpTrace.ps1') -Validate
 Write-Output 'Validation PASS: compile/layout/schema/source/ownership/bounds/loss; no native trace-control call';return
}
$principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
Require ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'MANUAL_ELEVATED_POWERSHELL_REQUIRED'
Require ($RunId -ne [Guid]::Empty) 'FRESH_RUN_ID_REQUIRED'
$local=[IO.Path]::GetFullPath($env:LOCALAPPDATA)
Require ($local -notlike '\\*' -and ([IO.DriveInfo]::new([IO.Path]::GetPathRoot($local))).DriveType -eq 'Fixed') 'LOCAL_DISK_REQUIRED'
$raw=Join-Path $local ("PR81TcpTrace/"+$RunId.ToString())
$control=Join-Path $root ("tmp/pr81-tcp-capture-control/"+$RunId.ToString())
function NoReparse([string]$path){
 $item=Get-Item -LiteralPath $path -Force
 while($null -ne $item){Require (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_REJECT';$item=$item.Parent}
}
function Put([string]$path,$data){
 Require (!(Test-Path -LiteralPath $path)) 'NO_RECORD_REUSE'
 [IO.File]::WriteAllText($path,($data|ConvertTo-Json -Depth 7),[Text.UTF8Encoding]::new($false))
}
if($Mode -eq 'Watchdog'){
 NoReparse $raw
 Put (Join-Path $raw 'watchdog-ready.json') @{run_id=$RunId.ToString();deadline=$Deadline}
 while([PR81TcpV2.Native]::Clock() -lt $Deadline){[Threading.Thread]::Sleep(50)}
 $handle=[uint64]0;$marker=Join-Path $raw 'created.json'
 if(Test-Path -LiteralPath $marker){$handle=[uint64](Get-Content -LiteralPath $marker -Raw|ConvertFrom-Json).handle}
 $stop=[PR81TcpV2.Native]::Stop($RunId,$handle);$after=[PR81TcpV2.Native]::Query($RunId)
 Put (Join-Path $raw 'watchdog-ended.json') @{stop_code=$stop.Code;disable_attempted=$stop.DisableAttempted;disable_code=$(if($stop.DisableAttempted){$stop.DisableCode}else{$null});query_code=$after.Code;absent=($after.Code -eq 4201)}
 return
}
Require (!(Test-Path -LiteralPath $raw) -and !(Test-Path -LiteralPath $control)) 'RUN_DIRECTORY_REUSE'
NoReparse $local;NoReparse $root
foreach($newPath in @($raw,$control)){
 $existingParent=Split-Path -Path $newPath -Parent
 while(!(Test-Path -LiteralPath $existingParent)){$existingParent=Split-Path -Path $existingParent -Parent}
 NoReparse $existingParent
}
[IO.Directory]::CreateDirectory($raw)|Out-Null
$acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetAccessRuleProtection($true,$false)
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;$acl.SetOwner($sid)
foreach($identity in @($sid,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))){
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
}
NoReparse $raw
Set-Acl -LiteralPath $raw -AclObject $acl
$check=Get-Acl -LiteralPath $raw
Require ($check.AreAccessRulesProtected -and @($check.Access).Count -eq 3 -and @($check.Access|Where-Object {$_.AccessControlType -ne 'Allow' -or $_.FileSystemRights -ne 'FullControl' -or $_.IsInherited -or $_.InheritanceFlags -ne 'ContainerInherit, ObjectInherit' -or $_.PropagationFlags -ne 'None'}).Count -eq 0) 'RAW_ACL'
$actualSids=@($check.Access|ForEach-Object {$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value}|Sort-Object)
$expectedSids=@($sid.Value,'S-1-5-18','S-1-5-32-544'|Sort-Object)
Require (($actualSids -join ',') -ceq ($expectedSids -join ',') -and $check.Owner -eq $sid.Translate([Security.Principal.NTAccount]).Value) 'RAW_ACL_IDENTITIES'
[IO.Directory]::CreateDirectory($control)|Out-Null;NoReparse $control
$machine=(Get-ItemPropertyValue -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid)
$hostHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($machine)))).Replace('-','').ToLower();$machine=$null
Require ($hostHash -eq $bundle.host_hash) 'SAME_HOST_REQUIRED'
Put (Join-Path $raw 'ownership.json') @{run_id=$RunId.ToString();profile_sha256=$bundle.profile_sha256;host_hash=$hostHash}
Put (Join-Path $control 'armed.json') @{run_id=$RunId.ToString();host_hash=$hostHash;profile_sha256=$bundle.profile_sha256;expires_utc=[DateTime]::UtcNow.AddSeconds(300).ToString('o')}
Write-Output ("ARMED "+$RunId.ToString()+": send this RunId to Codex; capture has not started.")
$requestPath=Join-Path $control 'fixture-request.json';$until=[PR81TcpV2.Native]::Clock()+300000
while(!(Test-Path -LiteralPath $requestPath) -and [PR81TcpV2.Native]::Clock() -lt $until){[Threading.Thread]::Sleep(50)}
Require (Test-Path -LiteralPath $requestPath) 'ARM_EXPIRED_NO_CAPTURE'
$request=Get-Content -LiteralPath $requestPath -Raw|ConvertFrom-Json
Require ($request.run_id -eq $RunId.ToString() -and $request.host_hash -eq $hostHash -and $request.source_identity -eq $bundle.source_identity) 'FIXTURE_REQUEST_BINDING'
$fixture=Get-Process -Id $request.fixture_pid
Require ($fixture.StartTime.ToUniversalTime().Ticks -eq $request.fixture_start_ticks -and (Get-FileHash -LiteralPath $fixture.Path).Hash.ToLower() -in $bundle.python_hashes) 'LOCAL_FIXTURE_PROCESS'
Require ($null -ne $fixture -and !$fixture.HasExited) 'FIXTURE_PROCESS_ENDED'
$existing=[PR81TcpV2.Native]::Query($RunId);Write-Output ('Existing-session query numeric code: '+$existing.Code);Require ($existing.Code -eq 4201) 'EXISTING_OR_UNQUERYABLE_SESSION'
$deadline=[PR81TcpV2.Native]::Clock()+45000
$watchArgs=@('-NoProfile','-File',('"'+$PSCommandPath+'"'),'-Mode','Watchdog','-RunId',$RunId.ToString(),'-Deadline',$deadline.ToString())
$watch=Start-Process -FilePath (Join-Path $PSHOME 'pwsh.exe') -ArgumentList $watchArgs -WindowStyle Hidden -PassThru
$ready=Join-Path $raw 'watchdog-ready.json';$readyUntil=[PR81TcpV2.Native]::Clock()+5000
while(!(Test-Path -LiteralPath $ready) -and !$watch.HasExited -and [PR81TcpV2.Native]::Clock() -lt $readyUntil){[Threading.Thread]::Sleep(25)}
Require ((Test-Path -LiteralPath $ready) -and !$watch.HasExited) 'WATCHDOG_NOT_READY'
$wd=Get-Content -LiteralPath $ready -Raw|ConvertFrom-Json;Require ($wd.run_id -eq $RunId.ToString() -and $wd.deadline -eq $deadline) 'WATCHDOG_BINDING'
$handle=[uint64]0;$owned=$false;$snapshot=$null;$stop=$null;$failed=$false;$cleanupFailed=$false;$nativeStatus=[ordered]@{start=$null;limits_query=$null;enable=$null;snapshot_query=$null;disable=$null;stop=$null;absence_query=$null}
try{
 foreach($file in $bundle.source_hashes.PSObject.Properties){Require ((Get-FileHash -LiteralPath (Join-Path $root $file.Name)).Hash.ToLower() -eq $file.Value) 'SOURCE_CHANGED_BEFORE_START'}
 Require ([PR81TcpV2.Native]::Clock()+30000 -lt $deadline) 'INSUFFICIENT_CAPTURE_WINDOW'
 $start=[PR81TcpV2.Native]::Start($RunId,(Join-Path $raw 'capture.etl'));$nativeStatus.start=$start.Code;Require ($start.Code -eq 0) 'NATIVE_START_FAILED';$owned=$true;$handle=$start.Handle
 Put (Join-Path $raw 'created.json') @{run_id=$RunId.ToString();handle=$handle}
 $query=[PR81TcpV2.Native]::Query($RunId);$nativeStatus.limits_query=$query.Code;Require ($query.Code -eq 0 -and [PR81TcpV2.Native]::Owned($query.Stats,$RunId) -and [PR81TcpV2.Native]::Bounds($query.Stats)) 'QUERIED_LIMIT_MISMATCH'
 Require (!$watch.HasExited) 'WATCHDOG_EXIT_BEFORE_ENABLE'
 $nativeStatus.enable=[PR81TcpV2.Native]::EnableOnly($handle,$RunId);Require ($nativeStatus.enable -eq 0) 'ENABLE_FAILURE'
 Put (Join-Path $control 'active.json') @{run_id=$RunId.ToString();deadline=$deadline;profile_sha256=$bundle.profile_sha256}
 $done=Join-Path $control 'fixture-done.json'
 while(!(Test-Path -LiteralPath $done) -and !$watch.HasExited -and [PR81TcpV2.Native]::Clock() -lt $deadline){[Threading.Thread]::Sleep(25)}
 $snapshot=[PR81TcpV2.Native]::Query($RunId);$nativeStatus.snapshot_query=$snapshot.Code
}catch{$failed=$true}finally{
 if($owned){try{$stop=[PR81TcpV2.Native]::Stop($RunId,$handle);$nativeStatus.stop=$stop.Code;if($stop.DisableAttempted){$nativeStatus.disable=$stop.DisableCode}}catch{$cleanupFailed=$true}}
}
$after=$null;try{$after=[PR81TcpV2.Native]::Query($RunId);$nativeStatus.absence_query=$after.Code}catch{$cleanupFailed=$true}
$stopCode=if($null -eq $stop){-1}else{$stop.Code}
$absent=$null -ne $after -and $after.Code -eq 4201
Put (Join-Path $control 'stopped.json') @{run_id=$RunId.ToString();stop_code=$stopCode;absent=$absent;native_status=$nativeStatus;capture_failed=$failed;cleanup_failed=$cleanupFailed;profile_sha256=$bundle.profile_sha256;deadline=$deadline;finished_tick=[PR81TcpV2.Native]::Clock()}
if(!$absent){Write-Output 'CLEANUP UNVERIFIED: use the exact GUID-guarded emergency procedure in PR81_TCP_TRACE_MANUAL_PROCEDURE_V2.md.'}
Require (!$failed -and !$cleanupFailed -and $null -ne $stop -and $stop.DisableAttempted -and $stop.DisableCode -eq 0) 'CAPTURE_ABORTED_NO_EXPORT'
Require ($after.Code -eq 4201 -and $stop.Code -eq 0 -and $null -ne $snapshot -and $snapshot.Code -eq 0 -and [PR81TcpV2.Native]::Complete($stop.Stats)) 'INCOMPLETE_OR_CLEANUP_FAILURE'
Require (Test-Path -LiteralPath $done) 'FIXTURE_NOT_DONE_BEFORE_DEADLINE'
& (Join-Path $PSScriptRoot 'Sanitize-TcpTrace.ps1') -RawPath (Join-Path $raw 'capture.etl') -TargetPath $done -OutputPath (Join-Path $control 'sanitized.json') -RunId $RunId
Write-Output ('Raw records remain local/protected. Share only '+(Join-Path $control 'sanitized.json'))

