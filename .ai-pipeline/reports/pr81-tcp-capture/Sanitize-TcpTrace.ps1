param([string]$RawPath,[string]$TargetPath,[string]$OutputPath,[Guid]$RunId,[switch]$Validate)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../PR81_TCP_TRACE_EVENT_SCHEMA.json') -Raw | ConvertFrom-Json
function Convert-Address($value) {
 if($value -is [byte[]] -and $value.Length -eq 28 -and $value[0] -eq 23 -and $value[1] -eq 0){return $null}
 if($value -isnot [byte[]] -or $value.Length -ne 16 -or $value[0] -ne 2 -or $value[1] -ne 0){throw 'ADDRESS_FORMAT'}
 if($value[4] -ne 127 -or $value[5] -ne 0 -or $value[6] -ne 0 -or $value[7] -ne 1){return $null}
 return [int]$value[2]*256+[int]$value[3]
}
function Select-Connection($rows,$target) {
 $allowed=@{};foreach($e in $schema.Events){$allowed["$($e.Id):$($e.Version)"]=$e}
 $maps=@{};$parsed=[Collections.Generic.List[object]]::new()
 foreach($row in $rows) {
  $key="$($row.Id):$($row.Version)"
  if(!$allowed.ContainsKey($key)){throw 'UNKNOWN_EVENT_SCHEMA'}
  [xml]$xml=$allowed[$key].Template;$defs=@($xml.template.data)
  if($row.Values.Count -ne $defs.Count){throw 'FIELD_COUNT'}
  $data=@{}
  for($i=0;$i -lt $defs.Count;$i++){
   $value=$row.Values[$i];$def=$defs[$i]
   if($def.inType -eq 'win:Binary'){
    if($def.outType -ne 'win:SocketAddress'){throw 'BINARY_FIELD'}
    $data[$def.name]=Convert-Address $value
   }elseif($def.inType -eq 'win:Boolean'){
    if($value -isnot [bool]){throw 'BOOLEAN_TYPE'}
    $data[$def.name]=$value
   }else{
    if($value -isnot [byte] -and $value -isnot [uint16] -and $value -isnot [uint32] -and $value -isnot [uint64] -and $value -isnot [int16] -and $value -isnot [int32] -and $value -isnot [int64] -and $value -isnot [IntPtr]){throw 'NUMERIC_TYPE'}
    if($value -is [IntPtr]){$value=$value.ToInt64()}
    if([decimal]$value -lt 0){throw 'NEGATIVE_VALUE'}
    $data[$def.name]=[uint64]$value
   }
  }
  if(!$data.ContainsKey('Tcb')){throw 'NO_TCB'}
  if($data.Tcb -eq 0){throw 'ZERO_TCB'}
  $tcb=[string]$data.Tcb
  $localKey=if($data.ContainsKey('LocalAddress')){'LocalAddress'}elseif($data.ContainsKey('LocalSockAddr')){'LocalSockAddr'}else{$null}
  if($localKey){
   $remoteKey=if($localKey -eq 'LocalAddress'){'RemoteAddress'}else{'RemoteSockAddr'}
   $local=$data[$localKey];$remote=$data[$remoteKey]
   $pidKey=if($data.ContainsKey('ProcessId')){'ProcessId'}elseif($data.ContainsKey('Pid')){'Pid'}else{$null}
   $direction=if($local -eq $target.server_port -and $remote -eq $target.client_port){'server'}elseif($local -eq $target.client_port -and $remote -eq $target.server_port){'client'}else{$null}
   $binding="$local/$remote";if($maps.ContainsKey($tcb) -and $maps[$tcb].Binding -ne $binding){throw 'TCB_REUSE'}
   if(!$maps.ContainsKey($tcb)){$maps[$tcb]=@{Binding=$binding;Direction=$direction;PidVerified=$false}}
   if($pidKey -and $direction){
    if($data[$pidKey] -ne $target.fixture_pid){throw 'PID_MISMATCH'}
    $maps[$tcb].PidVerified=$true
   }
  }
  $parsed.Add(@{Id=$row.Id;Version=$row.Version;Time=$row.Utc;Data=$data;Tcb=$tcb})
 }
 $chosen=@($maps.Keys | Where-Object {$maps[$_].Direction -and $maps[$_].PidVerified})
 if(@($chosen|Where-Object {$maps[$_].Direction -eq 'server'}).Count -ne 1 -or @($chosen|Where-Object {$maps[$_].Direction -eq 'client'}).Count -ne 1){throw 'CONNECTION_AMBIGUOUS_OR_UNBOUND'}
 $output=[Collections.Generic.List[object]]::new()
 foreach($item in $parsed){
  if($item.Tcb -notin $chosen){continue}
  $safe=[ordered]@{event_id=$item.Id;version=$item.Version;utc=$item.Time;side=$maps[$item.Tcb].Direction;fields=[ordered]@{}}
  [xml]$xml=$allowed["$($item.Id):$($item.Version)"].Template
  foreach($def in @($xml.template.data)){
   if($def.inType -eq 'win:Pointer' -or $def.inType -eq 'win:Binary' -or $def.name -match 'Address|SockAddr|ProcessStartKey|^Pid$|^ProcessId$'){continue}
   $safe.fields[$def.name]=$item.Data[$def.name]
  }
  $output.Add($safe)
 }
 if($output.Count -gt 4096){throw 'EXPORT_COUNT'}
 return @($output.ToArray())
}
if($Validate){
 function Address([int]$port,[int]$first=127){return ,([byte[]](2,0,[byte]($port -shr 8),[byte]($port -band 255),$first,0,0,1,0,0,0,0,0,0,0,0))}
 $target=[pscustomobject]@{server_port=30101;client_port=30102;fixture_pid=30103}
 function Row([int]$id,[int]$version,[uint64]$tcb,[int]$local,[int]$remote,[int]$fixtureOwner,[int]$first=127){
  $ev=@($schema.Events|Where-Object {$_.Id -eq $id -and $_.Version -eq $version})[0]
  [xml]$xml=$ev.Template;$values=[Collections.Generic.List[object]]::new()
  foreach($f in @($xml.template.data)){
   $v=[uint32]0
   if($f.inType -eq 'win:Pointer'){$v=[uint64]0}
   if($f.name -eq 'Tcb'){$v=$tcb}
   if($f.name -in @('ProcessId','Pid')){$v=[uint32]$fixtureOwner}
   if($f.inType -eq 'win:Binary'){$v=if($f.name -match '^Local') {Address $local $first}else{Address $remote $first}}
   if($f.inType -eq 'win:Boolean'){$v=$false}
   $values.Add($v)
  }
  return [pscustomobject]@{Id=$id;Version=$version;Values=$values.ToArray();Utc='2026-01-01T00:00:00Z'}
 }
 $server=Row 1038 1 1 30101 30102 30103
 $client=Row 1038 1 2 30102 30101 30103
 $send=Row 1332 5 1 30101 30102 30103
 $foreign=Row 1038 1 4 80 90 99 192
 $rows=@($server,$client,$send,$foreign)
 $safe=@(Select-Connection $rows $target)
 if($safe.Count -ne 3 -or ($safe|ConvertTo-Json -Depth 8) -match '"Tcb"|"LocalAddress"|"ProcessStartKey"|192\.'){throw 'SAFE_EXPORT_FAILURE'}
 $ok=1
 function Reject($badrows){
  try{Select-Connection $badrows $target|Out-Null;throw 'ADVERSE_MISSED'}catch{if($_.Exception.Message -eq 'ADVERSE_MISSED'){throw}}
 }
 Reject @([pscustomobject]@{Id=9999;Version=0;Values=@();Utc='2026-01-01T00:00:00Z'});$ok++
 Reject @([pscustomobject]@{Id=1332;Version=99;Values=@();Utc='2026-01-01T00:00:00Z'});$ok++
 $bad=Row 1332 5 1 30101 30102 30103;$bad.Values[1]='Authorization: secret-content';Reject @($server,$client,$bad);$ok++
 Reject @($server,$client,(Row 1038 1 1 80 90 99 192));$ok++
 Reject @($server,$client,(Row 1038 1 3 30101 30102 30103));$ok++
 Reject @((Row 1038 1 1 30101 30102 99),$client,$send);$ok++
 foreach($bad in @('HTTP-body',[byte[]](1,2,3))){
  try{Convert-Address $bad|Out-Null;throw 'ADVERSE_MISSED'}catch{if($_.Exception.Message -eq 'ADVERSE_MISSED'){throw};$ok++}
 }
 Write-Output "Sanitizer checks=${ok}: matching connection only, unknown ID/version, string payload, reuse, ambiguity, PID and address rejection; no ETL read";return
}
if(!(Test-Path -LiteralPath $RawPath -PathType Leaf) -or (Get-Item -LiteralPath $RawPath).Length -gt 8MB){throw 'RAW_SIZE_OR_MISSING'}
$target=Get-Content -LiteralPath $TargetPath -Raw|ConvertFrom-Json
if($target.run_id -ne $RunId.ToString() -or $target.source_identity -ne 'ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490'){throw 'TARGET_BINDING'}
if($target.correlation -notmatch ('^d1-native-'+[regex]::Escape($RunId.ToString())+'-r[0-9]{2}$') -or $target.server_port -notin 1..65535 -or $target.client_port -notin 1..65535 -or $target.fixture_pid -le 0){throw 'TARGET_FORMAT'}
$rows=[Collections.Generic.List[object]]::new()
Get-WinEvent -Path $RawPath -Oldest -ErrorAction Stop | ForEach-Object {
 # No message rendering or ToXml dump; ETL headers/control events never exported.
 if($_.ProviderId.ToString() -eq '2f07e2ee-15db-40f1-90ef-9d7ba282188a'){
  if($rows.Count -ge 32768){throw 'RAW_EVENT_COUNT'}
  $rows.Add([pscustomobject]@{Id=$_.Id;Version=$_.Version;Utc=$_.TimeCreated.ToUniversalTime().ToString('o');Values=@($_.Properties|ForEach-Object {$_.Value})})
 }
}
$events=Select-Connection ($rows.ToArray()) $target
$payload=[ordered]@{run_id=$RunId.ToString();source_identity=$target.source_identity;server_port=$target.server_port;client_port=$target.client_port;fixture_pid=$target.fixture_pid;correlation=$target.correlation;profile_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot '../PR81_TCP_TRACE_CAPTURE_PROFILE.json')).Hash.ToLower();schema_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot '../PR81_TCP_TRACE_EVENT_SCHEMA.json')).Hash.ToLower();observations='Native events only; missing coverage is UNKNOWN, no wire FIN claim';events=$events}
$json=$payload|ConvertTo-Json -Depth 8
if([Text.Encoding]::UTF8.GetByteCount($json) -gt 1MB -or (Test-Path -LiteralPath $OutputPath)){throw 'EXPORT_SIZE_OR_REUSE'}
[IO.File]::WriteAllText($OutputPath,$json,[Text.UTF8Encoding]::new($false))
Write-Output 'Sanitized metadata exported; no raw event/header/address/pointer/message fields shared.'

