# Sanitizer-owned production provenance/envelope boundary. No trace-control, raw content or exception rendering.
function ExportRequire($condition,[string]$code){if(!$condition){throw $code}}
function ExportHash([byte[]]$bytes){return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()}
function New-CaptureProvenance([Guid]$id,$bundle,$stop,$nativeStatus,[long]$deadline,[long]$finished){
 $stats=[ordered]@{}
 foreach($name in @('BufferSize','MinimumBuffers','MaximumBuffers','MaximumFileSize','NumberOfBuffers','LogFileMode','EnableFlags','EventsLost','LogBuffersLost','RealTimeBuffersLost','BuffersWritten')){$stats[$name]=$stop.Stats.$name}
 return [pscustomobject]@{run_id=$id.ToString();owned_run_id=$stop.Stats.Wnode.Guid.ToString();source_identity=$bundle.source_identity;profile_sha256=$bundle.profile_sha256;schema_sha256=$bundle.files.'../PR81_TCP_TRACE_EVENT_SCHEMA_V2.json';deadline=$deadline;finished_tick=$finished;capture_failed=$false;cleanup_failed=$false;absent=$true;native_status=$nativeStatus;stats=[pscustomobject]$stats}
}
function Read-ExportJson([string]$path,[int]$maxBytes=16384){
 $item=Get-Item -LiteralPath $path -Force
 ExportRequire ($item -is [IO.FileInfo] -and $item.Length -le $maxBytes) 'PROVENANCE_RECORD_SIZE'
 $ancestor=$item
 while($null -ne $ancestor){ExportRequire (($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'PROVENANCE_REPARSE';$ancestor=if($ancestor -is [IO.FileInfo]){$ancestor.Directory}else{$ancestor.Parent}}
 return [IO.File]::ReadAllText($path)|ConvertFrom-Json
}
function Get-ExportInputs([string]$targetPath,[Guid]$id){
 $helper=$PSScriptRoot;$root=[IO.Path]::GetFullPath((Join-Path $helper '../../..'))
 $control=[IO.Path]::GetFullPath((Join-Path $root ('tmp/pr81-tcp-capture-control/'+$id.ToString())))
 ExportRequire ([IO.Path]::GetFullPath($targetPath) -ceq (Join-Path $control 'fixture-done.json')) 'PROVENANCE_CONTROL_PATH'
 $bundle=Read-ExportJson (Join-Path $helper 'bundle.json')
 foreach($file in $bundle.files.PSObject.Properties){ExportRequire ((Get-FileHash -LiteralPath (Join-Path $helper $file.Name)).Hash.ToLower() -ceq $file.Value) 'EXPORT_BUNDLE_CHANGED'}
 foreach($file in $bundle.source_hashes.PSObject.Properties){ExportRequire ((Get-FileHash -LiteralPath (Join-Path $root $file.Name)).Hash.ToLower() -ceq $file.Value) 'EXPORT_SOURCE_CHANGED'}
 $target=Read-ExportJson $targetPath
 $receiptPath=Join-Path $root ('tmp/pr81-tcp-native-'+$id.ToString()+'.json')
 $receipt=Read-ExportJson $receiptPath 1048576
 return [pscustomobject]@{Bundle=$bundle;ProfileBytes=[IO.File]::ReadAllBytes((Join-Path $helper '../PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json'));SchemaBytes=[IO.File]::ReadAllBytes((Join-Path $helper '../PR81_TCP_TRACE_EVENT_SCHEMA_V2.json'));Target=$target;Armed=(Read-ExportJson (Join-Path $control 'armed.json'));Request=(Read-ExportJson (Join-Path $control 'fixture-request.json'));Active=(Read-ExportJson (Join-Path $control 'active.json'));Stopped=(Read-ExportJson (Join-Path $control 'stopped.json'));Capture=(Read-ExportJson (Join-Path $control 'capture-provenance.json'));Receipt=$receipt;ReceiptHash=(Get-FileHash -LiteralPath $receiptPath).Hash.ToLower()}
}
function Assert-ExportInputs($inputs,[Guid]$id){
 ExportRequire ($id -ne [Guid]::Empty) 'PROVENANCE_RUN_REQUIRED'
 $bundle=$inputs.Bundle
 ExportRequire ($bundle.helper_version -ceq '6.1') 'UNSUPPORTED_EXPORT_MANIFEST'
 # This is the only supported reviewed profile, and its actual bytes must independently reproduce it.
 $profile=ExportHash $inputs.ProfileBytes
 ExportRequire ($profile -ceq 'ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f') 'UNSUPPORTED_PROFILE_BYTES'
 ExportRequire ($bundle.profile_sha256 -ceq $profile -and $bundle.files.'../PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json' -ceq $profile) 'MANIFEST_PROFILE_MISMATCH'
 $schemaIdentity=ExportHash $inputs.SchemaBytes
 ExportRequire ($schemaIdentity -ceq '79c27947d2e0188a8e6f0c2cdc90329844f7e2f189d6966b2424cdf13dcc8e01' -and $bundle.files.'../PR81_TCP_TRACE_EVENT_SCHEMA_V2.json' -ceq $schemaIdentity) 'MANIFEST_SCHEMA_MISMATCH'
 ExportRequire ($bundle.source_identity -ceq 'ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490') 'MANIFEST_SOURCE_MISMATCH'
 foreach($record in @($inputs.Armed,$inputs.Request,$inputs.Active,$inputs.Target,$inputs.Stopped,$inputs.Capture,$inputs.Receipt)){
  ExportRequire ($null -ne $record -and $record.run_id -ceq $id.ToString() -and $record.profile_sha256 -ceq $profile) 'CAPTURE_PROFILE_BINDING'
 }
 foreach($record in @($inputs.Request,$inputs.Target,$inputs.Capture,$inputs.Receipt)){ExportRequire ($record.source_identity -ceq $bundle.source_identity) 'CAPTURE_SOURCE_BINDING'}
 ExportRequire ($inputs.Armed.host_hash -ceq $bundle.host_hash -and $inputs.Request.host_hash -ceq $bundle.host_hash -and $inputs.Request.fixture_pid -eq $inputs.Target.fixture_pid) 'CAPTURE_HOST_PROCESS_BINDING'
 ExportRequire ($inputs.Target.receipt_sha256 -ceq $inputs.ReceiptHash -and $inputs.ReceiptHash -cmatch '^[0-9a-f]{64}$') 'CAPTURE_RECEIPT_BINDING'
 $capture=$inputs.Capture
 ExportRequire (Test-Json -Json ($capture|ConvertTo-Json -Depth 8 -Compress) -SchemaFile (Join-Path $PSScriptRoot 'CAPTURE_PROVENANCE_SCHEMA.json') -ErrorAction Stop) 'CAPTURE_METADATA_SCHEMA'
 ExportRequire ($capture.owned_run_id -ceq $id.ToString()) 'CAPTURE_OWNERSHIP'
 ExportRequire ($capture.deadline -eq $inputs.Active.deadline -and $capture.deadline -eq $inputs.Stopped.deadline -and $capture.finished_tick -ge ($capture.deadline-45000) -and $capture.finished_tick -le $capture.deadline -and ($inputs.Stopped.finished_tick -is [long] -or $inputs.Stopped.finished_tick -is [int]) -and $inputs.Stopped.finished_tick -ge ($capture.deadline-45000) -and $inputs.Stopped.finished_tick -le $capture.finished_tick) 'CAPTURE_DEADLINE_BINDING'
 ExportRequire ($inputs.Stopped.capture_failed -is [bool] -and !$inputs.Stopped.capture_failed -and $inputs.Stopped.cleanup_failed -is [bool] -and !$inputs.Stopped.cleanup_failed -and $inputs.Stopped.absent -is [bool] -and $inputs.Stopped.absent -and $inputs.Stopped.stop_code -eq 0) 'CAPTURE_INCOMPLETE'
 foreach($name in @('start','limits_query','enable','snapshot_query','disable','stop','absence_query')){
  $value=$inputs.Stopped.native_status.$name
  ExportRequire (($value -is [int] -or $value -is [long] -or $value -is [uint32]) -and $value -eq $capture.native_status.$name) 'CAPTURE_NATIVE_STATUS_BINDING'
 }
 $stats=[PR81TcpV61.Stats]::new()
 foreach($field in $capture.stats.PSObject.Properties){$stats.($field.Name)=$field.Value}
 ExportRequire ([PR81TcpV61.Native]::Bounds($stats) -and [PR81TcpV61.Native]::Complete($stats)) 'CAPTURE_BOUNDS_OR_LOSS'
 return [pscustomobject]@{Profile=$profile;Schema=$schemaIdentity}
}
function New-SanitizedEnvelope($rows,$inputs,[Guid]$id){
 $identity=Assert-ExportInputs $inputs $id
 $target=$inputs.Target
 # Preserve the original target gate; fixture failure itself is forensic evidence, not a replay/export authorization.
 ExportRequire ($target.correlation -cmatch ('^d1-native-'+[regex]::Escape($id.ToString())+'-r[0-9]{2}$') -and $target.server_port -in 1..65535 -and $target.client_port -in 1..65535 -and $target.fixture_pid -gt 0) 'TARGET_FORMAT'
 $events=Select-Connection $rows $target
 return [ordered]@{run_id=$id.ToString();source_identity=$target.source_identity;server_port=$target.server_port;client_port=$target.client_port;fixture_pid=$target.fixture_pid;correlation=$target.correlation;profile_sha256=$identity.Profile;schema_sha256=$identity.Schema;observations='Native events only; missing coverage is UNKNOWN, no wire FIN claim';events=@($events)}
}
function Write-SanitizedExport($rows,$inputs,[Guid]$id,[string]$outputPath){
 $payload=New-SanitizedEnvelope $rows $inputs $id
 $json=$payload|ConvertTo-Json -Depth 8
 ExportRequire (Test-Json -Json $json -SchemaFile (Join-Path $PSScriptRoot 'SANITIZED_EXPORT_SCHEMA.json') -ErrorAction Stop) 'EXPORT_ENVELOPE_SCHEMA'
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes($json)
 ExportRequire ($bytes.Length -le 1MB) 'EXPORT_SIZE'
 $stream=[IO.FileStream]::new($outputPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
