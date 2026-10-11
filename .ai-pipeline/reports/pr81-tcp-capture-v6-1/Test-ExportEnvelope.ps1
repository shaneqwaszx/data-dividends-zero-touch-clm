param([string]$OutputPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Load the production selection and envelope functions, running the preserved 19 selection regressions first.
. (Join-Path $PSScriptRoot 'Sanitize-TcpTrace.ps1') -Validate
function Check($ok,[string]$code){if(!$ok){throw ('V61_ENVELOPE_TEST_'+$code)}}
$testBundle=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'bundle.json') -Raw|ConvertFrom-Json
$testId=[Guid]::NewGuid()
$testSource=$testBundle.source_identity;$testProfile=$testBundle.profile_sha256
$testReceipt=[pscustomobject]@{synthetic=$true;run_id=$testId.ToString();profile_sha256=$testProfile;source_identity=$testSource}
$receiptText=$testReceipt|ConvertTo-Json -Compress
$testReceiptHash=ExportHash ([Text.Encoding]::UTF8.GetBytes($receiptText))
$target=[pscustomobject]@{run_id=$testId.ToString();profile_sha256=$testProfile;source_identity=$testSource;fixture_pid=30103;server_port=30101;client_port=30102;correlation=('d1-native-'+$testId.ToString()+'-r01');exit_code=0;receipt_sha256=$testReceiptHash;extra_http_body='SYNTHETIC_BODY_MUST_NOT_EXPORT'}
$native=[ordered]@{start=0;limits_query=0;enable=0;snapshot_query=0;disable=0;stop=0;absence_query=4201}
$stats=[PR81TcpV61.Stats]::new();$node=[PR81TcpV61.Wnode]::new();$node.Guid=$testId;$stats.Wnode=$node
$stats.BufferSize=64;$stats.MinimumBuffers=4;$stats.MaximumBuffers=16;$stats.MaximumFileSize=8;$stats.NumberOfBuffers=4;$stats.LogFileMode=0x10400002;$stats.BuffersWritten=1
$stop=[PR81TcpV61.Result]::new();$stop.Code=0;$stop.Stats=$stats
$capture=New-CaptureProvenance $testId $testBundle $stop $native 45000 35000
$baseline=[pscustomobject]@{
 Bundle=$testBundle
 ProfileBytes=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot '../PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json'))
 SchemaBytes=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot '../PR81_TCP_TRACE_EVENT_SCHEMA_V2.json'))
 Target=$target
 Armed=[pscustomobject]@{run_id=$testId.ToString();profile_sha256=$testProfile;host_hash=$testBundle.host_hash}
 Request=[pscustomobject]@{run_id=$testId.ToString();profile_sha256=$testProfile;host_hash=$testBundle.host_hash;source_identity=$testSource;fixture_pid=30103}
 Active=[pscustomobject]@{run_id=$testId.ToString();profile_sha256=$testProfile;deadline=45000}
 Stopped=[pscustomobject]@{run_id=$testId.ToString();profile_sha256=$testProfile;deadline=45000;finished_tick=34000;capture_failed=$false;cleanup_failed=$false;absent=$true;stop_code=0;native_status=$native}
 Capture=$capture
 Receipt=$testReceipt
 ReceiptHash=$testReceiptHash
}
$testRows=$rows
$cases=[Collections.Generic.List[object]]::new()
$work=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('pr81-v61-export-test-'+[Guid]::NewGuid().ToString())))
$null=[IO.Directory]::CreateDirectory($work)
$created=[Collections.Generic.List[string]]::new()
function CloneInputs(){return ($baseline|ConvertTo-Json -Depth 20 -Compress)|ConvertFrom-Json}
function Case([string]$name,[scriptblock]$change,[bool]$shouldPass=$false){
 $inputs=CloneInputs
 & $change $inputs
 $path=[IO.Path]::GetFullPath((Join-Path $work ($name+'.json')))
 Check ($path.StartsWith($work+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) 'EXACT_TEST_PATH'
 $rejected=$false
 try{Write-SanitizedExport $testRows $inputs $testId $path}catch{$rejected=$true}
 if($shouldPass){
  Check (!$rejected -and [IO.File]::Exists($path)) ('POSITIVE_'+$name);$created.Add($path)
  $json=[IO.File]::ReadAllText($path);$output=$json|ConvertFrom-Json
  Check (Test-Json -Json $json -SchemaFile (Join-Path $PSScriptRoot 'SANITIZED_EXPORT_SCHEMA.json')) 'ACTUAL_OUTPUT_SCHEMA'
  Check ($output.profile_sha256 -ceq (ExportHash $baseline.ProfileBytes) -and $output.profile_sha256 -ceq $testProfile) 'RECOMPUTABLE_ACTUAL_ENVELOPE'
  Check (@($output.PSObject.Properties).Count -eq 10 -and @($output.events).Count -eq 7) 'UNCHANGED_ENVELOPE_FIELDS'
  Check ($json -notmatch 'SYNTHETIC_BODY_MUST_NOT_EXPORT|extra_http_body|"Tcb"|"LocalAddress"|"ProcessStartKey"|Authorization') 'NO_SENSITIVE_FIELDS'
 }else{Check ($rejected -and ![IO.File]::Exists($path)) ('NEGATIVE_NO_EXPORT_'+$name)}
 $cases.Add(@{name=$name;expected_accept=$shouldPass;pass=$true;export_created=$shouldPass})
}
try{
 Case 'exact_v6_profile_actual_writer' {} $true
 # Original failing HTTP can still supply complete diagnostic metadata; no new requirement for fixture PASS is invented.
 Case 'failed_fixture_complete_capture' {param($i);$i.Target.exit_code=1} $true
 foreach($record in @('Armed','Request','Active','Target','Stopped','Capture','Receipt')){
  Case ('stale_v2_'+$record) {param($i);$i.$record.profile_sha256='74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1'}
  Case ('missing_profile_'+$record) {param($i);$i.$record.PSObject.Properties.Remove('profile_sha256')}
 }
 Case 'modified_profile_bytes' {param($i);$i.ProfileBytes=[byte[]](@($i.ProfileBytes)+32)}
 Case 'manifest_profile_mismatch' {param($i);$i.Bundle.profile_sha256='74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1'}
 Case 'manifest_member_mismatch' {param($i);$i.Bundle.files.'../PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json'=('f'*64)}
 Case 'unsupported_profile_identity' {param($i);$i.Bundle.profile_sha256=('f'*64);$i.Target.profile_sha256=('f'*64)}
 Case 'unsupported_profile_bytes' {param($i);$i.ProfileBytes=[Text.Encoding]::UTF8.GetBytes('{}')}
 Case 'missing_profile_bytes' {param($i);$i.ProfileBytes=$null}
 Case 'unsupported_manifest_version' {param($i);$i.Bundle.helper_version='6'}
 Case 'missing_capture_metadata' {param($i);$i.Capture=$null}
 Case 'incomplete_capture_metadata' {param($i);$i.Capture.PSObject.Properties.Remove('stats')}
 Case 'failed_capture' {param($i);$i.Capture.capture_failed=$true}
 Case 'failed_cleanup' {param($i);$i.Stopped.cleanup_failed=$true}
 Case 'absence_not_proven' {param($i);$i.Stopped.absent=$false}
 Case 'invalid_capture_flag_type' {param($i);$i.Capture.capture_failed='false'}
 Case 'missing_enable_result' {param($i);$i.Capture.native_status.enable=$null}
 Case 'conflicting_native_status' {param($i);$i.Stopped.native_status.disable=1168}
 Case 'native_status_wrong_type' {param($i);$i.Stopped.native_status.stop='0'}
 Case 'wrong_owned_run' {param($i);$i.Capture.owned_run_id=[Guid]::NewGuid().ToString()}
 Case 'wrong_target_run' {param($i);$i.Target.run_id=[Guid]::NewGuid().ToString()}
 Case 'wrong_source' {param($i);$i.Target.source_identity=('f'*64)}
 Case 'wrong_request_pid' {param($i);$i.Request.fixture_pid=99999}
 Case 'missing_receipt_metadata' {param($i);$i.Receipt=$null}
 Case 'wrong_receipt_hash' {param($i);$i.ReceiptHash=('f'*64)}
 Case 'schema_manifest_mismatch' {param($i);$i.Bundle.files.'../PR81_TCP_TRACE_EVENT_SCHEMA_V2.json'=('f'*64)}
 Case 'modified_schema_bytes' {param($i);$i.SchemaBytes=[byte[]](@($i.SchemaBytes)+32)}
 Case 'deadline_conflict' {param($i);$i.Active.deadline=46000}
 Case 'finished_after_deadline' {param($i);$i.Capture.finished_tick=45001}
 foreach($field in @('EventsLost','LogBuffersLost','RealTimeBuffersLost')){
  Case ('loss_'+$field) {param($i);$i.Capture.stats.$field=1}
 }
 Case 'overwrite_possible' {param($i);$i.Capture.stats.BuffersWritten=127}
 Case 'old_logging_mode' {param($i);$i.Capture.stats.LogFileMode=0x10000002}
 Case 'unexpected_capture_field' {param($i);$i.Capture|Add-Member NoteProperty extra_http_body 'SYNTHETIC_BODY_MUST_NOT_EXPORT'}
 # Complete real safe-record IO uses the production reader. No ETL, native trace or seeder is involved.
 $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
 $control=[IO.Path]::GetFullPath((Join-Path $root ('tmp/pr81-tcp-capture-control/'+$testId.ToString())))
 $receiptPath=[IO.Path]::GetFullPath((Join-Path $root ('tmp/pr81-tcp-native-'+$testId.ToString()+'.json')))
 Check (![IO.Directory]::Exists($control) -and ![IO.File]::Exists($receiptPath)) 'FRESH_SYNTHETIC_RECORDS'
 $ioFiles=[Collections.Generic.List[string]]::new()
 $null=[IO.Directory]::CreateDirectory($control)
 try{
  foreach($pair in @(@('armed.json','Armed'),@('fixture-request.json','Request'),@('active.json','Active'),@('fixture-done.json','Target'),@('stopped.json','Stopped'),@('capture-provenance.json','Capture'))){
   $path=Join-Path $control $pair[0];[IO.File]::WriteAllText($path,($baseline.($pair[1])|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$ioFiles.Add($path)
  }
  [IO.File]::WriteAllText($receiptPath,$receiptText,[Text.UTF8Encoding]::new($false));$ioFiles.Add($receiptPath)
  $input=Get-ExportInputs (Join-Path $control 'fixture-done.json') $testId
  $path=Join-Path $work 'real_safe_record_io.json';Write-SanitizedExport $testRows $input $testId $path;$created.Add($path)
  Check (([IO.File]::ReadAllText($path)|ConvertFrom-Json).profile_sha256 -ceq $testProfile) 'ACTUAL_READER_WRITER_BINDING'
  $cases.Add(@{name='real_safe_record_reader_and_actual_writer';pass=$true;expected_accept=$true;export_created=$true})
  # Missing capture input must fail at the reader, before any raw event access/output.
  $capturePath=Join-Path $control 'capture-provenance.json';[IO.File]::Delete($capturePath)
  $rejected=$false;try{$null=Get-ExportInputs (Join-Path $control 'fixture-done.json') $testId}catch{$rejected=$true}
  Check $rejected 'ACTUAL_READER_MISSING_RECORD'
  $cases.Add(@{name='real_reader_incomplete_capture';pass=$true;expected_accept=$false;export_created=$false})
 }finally{
  foreach($path in $ioFiles){
   $resolved=[IO.Path]::GetFullPath($path)
   Check ($resolved.StartsWith($control+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or $resolved -ceq $receiptPath) 'OWNED_IO_CLEANUP'
   if([IO.File]::Exists($resolved)){[IO.File]::Delete($resolved)}
  }
  [IO.Directory]::Delete($control,$false)
 }
 # CreateNew preserves any existing output; a successful rerun cannot overwrite evidence.
 $existing=Join-Path $work 'existing_output.json';[IO.File]::WriteAllText($existing,'synthetic-preserved');$created.Add($existing)
 $rejected=$false;try{Write-SanitizedExport $testRows $baseline $testId $existing}catch{$rejected=$true}
 Check ($rejected -and [IO.File]::ReadAllText($existing) -ceq 'synthetic-preserved') 'NO_OUTPUT_REUSE'
 $cases.Add(@{name='existing_output_preserved';pass=$true;expected_accept=$false;export_created=$false})
}finally{
 foreach($path in $created){Check ([IO.Path]::GetFullPath($path).StartsWith($work+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) 'OWNED_TEMP_CLEANUP';if([IO.File]::Exists($path)){[IO.File]::Delete($path)}}
 [IO.Directory]::Delete($work,$false)
}
$result=@{helper_version='6.1';case_count=$cases.Count;positive_count=@($cases|Where-Object {$_.expected_accept}).Count;negative_count=@($cases|Where-Object {!$_.expected_accept}).Count;failed_cases=0;production_envelope_and_writer_exercised=$true;real_safe_record_reader_exercised=$true;raw_etl_accessed=$false;native_trace_control_invoked=$false;fixture_executed=$false;cases=$cases}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))}
Write-Output ('V6.1 actual export envelope PASS: '+$cases.Count+' cases; positives='+$result.positive_count+'; negatives='+$result.negative_count+'; actual writer/reader, no false output; no ETL/fixture')
