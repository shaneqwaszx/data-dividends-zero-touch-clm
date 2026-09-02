[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Start", "Stop", "Reset", "Status")]
    [string]$Action
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$script:RuntimeDirectory = Join-Path $script:RepositoryRoot ".runtime"
$script:StatePath = Join-Path $script:RuntimeDirectory "demo-processes.json"
$script:StateTemporaryPath = Join-Path $script:RuntimeDirectory "demo-processes.json.tmp"
$script:StateSchemaVersion = 1
$script:BackendPort = 8000
$script:FrontendPort = 5173
$script:HealthTimeoutSeconds = 30
$script:StopTimeoutSeconds = 15
$script:RequiredRunningRoles = @("backend", "frontend")
$script:BackendDirectory = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot "apps\backend"))
$script:FrontendDirectory = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot "apps\frontend"))
$script:PythonPath = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot ".venv\Scripts\python.exe"))
$script:VitePath = [IO.Path]::GetFullPath((Join-Path $script:FrontendDirectory "node_modules\vite\bin\vite.js"))

function Write-DemoError {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

function Assert-SafeRuntimePath {
    if (-not (Test-SamePath -Left $script:RuntimeDirectory -Right (Join-Path $script:RepositoryRoot ".runtime"))) {
        throw "The runtime directory is outside the repository. No lifecycle action was taken."
    }
    if (Test-Path -LiteralPath $script:RuntimeDirectory) {
        $runtimeItem = Get-Item -LiteralPath $script:RuntimeDirectory -Force
        if (-not $runtimeItem.PSIsContainer -or
            (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw "The fixed .runtime path is not a normal repository directory. No lifecycle action was taken."
        }
    }
    foreach ($candidate in @($script:StatePath, $script:StateTemporaryPath)) {
        if (Test-Path -LiteralPath $candidate) {
            $item = Get-Item -LiteralPath $candidate -Force
            if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
                throw "A runtime metadata path is not a normal file. No lifecycle action was taken."
            }
        }
    }
}

function Test-SamePath {
    param([string]$Left, [string]$Right)
    if ([string]::IsNullOrWhiteSpace($Left) -or [string]::IsNullOrWhiteSpace($Right)) {
        return $false
    }
    try {
        $normalizedLeft = [IO.Path]::GetFullPath($Left)
        $normalizedRight = [IO.Path]::GetFullPath($Right)
    }
    catch {
        return $false
    }
    return [StringComparer]::OrdinalIgnoreCase.Equals($normalizedLeft, $normalizedRight)
}

function Get-ListenerProcessIds {
    param([int]$Port)
    $connections = @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    )
    return @($connections | ForEach-Object { [int]$_.OwningProcess } | Sort-Object -Unique)
}

function Test-ProcessExists {
    param([int]$ProcessId)
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function ConvertTo-UtcCreationInstant {
    param([object]$Value)
    if ($null -eq $Value) {
        throw "Creation time is missing."
    }
    if ($Value -is [DateTimeOffset]) {
        return ([DateTimeOffset]$Value).ToUniversalTime()
    }
    if ($Value -is [DateTime]) {
        $dateTime = [DateTime]$Value
        if ($dateTime.Kind -eq [DateTimeKind]::Unspecified) {
            throw "Creation time has no timezone information."
        }
        return [DateTimeOffset]::new($dateTime).ToUniversalTime()
    }
    if ($Value -isnot [string]) {
        throw "Creation time has an unsupported type."
    }

    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text) -or $text -notmatch "(?:[zZ]|[+-]\d{2}:\d{2})$") {
        throw "Creation time is not an unambiguous ISO-8601 instant."
    }
    $instant = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse(
        $text,
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::RoundtripKind,
        [ref]$instant
    )) {
        throw "Creation time could not be parsed."
    }
    return $instant.ToUniversalTime()
}

function Test-SameCreationTime {
    param([object]$Left, [object]$Right)
    try {
        $leftUtc = ConvertTo-UtcCreationInstant -Value $Left
        $rightUtc = ConvertTo-UtcCreationInstant -Value $Right
        # Win32_Process and Get-Process can disagree by sub-microsecond precision.
        # One millisecond retains a narrow PID-reuse guard while permitting the
        # documented fallback when CIM access is denied.
        return [Math]::Abs(($leftUtc - $rightUtc).TotalMilliseconds) -le 1
    }
    catch {
        return $false
    }
}

function Test-PortAvailable {
    param([int]$Port)
    $listener = $null
    try {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $listener) {
            $listener.Stop()
        }
    }
}

function Get-ProcessIdentityFallback {
    param([int]$ProcessId)
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        $path = [string]$process.Path
        if ([string]::IsNullOrWhiteSpace($path)) {
            return $null
        }
        return [pscustomobject]@{
            pid = [int]$process.Id
            creation_time_utc = $process.StartTime.ToUniversalTime().ToString("O")
            executable_path = [IO.Path]::GetFullPath($path)
            command_line = ""
        }
    }
    catch {
        return $null
    }
}

function Get-ProcessIdentity {
    param([int]$ProcessId)
    $item = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        return Get-ProcessIdentityFallback -ProcessId $ProcessId
    }
    if ($null -eq $item.CreationDate -or [string]::IsNullOrWhiteSpace([string]$item.ExecutablePath)) {
        return Get-ProcessIdentityFallback -ProcessId $ProcessId
    }
    return [pscustomobject]@{
        pid = [int]$item.ProcessId
        creation_time_utc = $item.CreationDate.ToUniversalTime().ToString("O")
        executable_path = [IO.Path]::GetFullPath([string]$item.ExecutablePath)
        command_line = [string]$item.CommandLine
    }
}

function Test-IsDescendantProcess {
    param(
        [int]$CandidateProcessId,
        [int]$AncestorProcessId
    )
    if ($CandidateProcessId -eq $AncestorProcessId) {
        return $true
    }
    $currentId = $CandidateProcessId
    for ($depth = 0; $depth -lt 16; $depth++) {
        $item = Get-CimInstance Win32_Process -Filter "ProcessId = $currentId" -ErrorAction SilentlyContinue
        if ($null -eq $item) {
            return $false
        }
        $parentId = [int]$item.ParentProcessId
        if ($parentId -eq $AncestorProcessId) {
            return $true
        }
        if ($parentId -le 0 -or $parentId -eq $currentId) {
            return $false
        }
        $currentId = $parentId
    }
    return $false
}

function Get-RoleExpectation {
    param([string]$Role)
    switch ($Role) {
        "backend" {
            return [pscustomobject]@{
                role = "backend"
                port = $script:BackendPort
                executable_path = $script:PythonPath
                executable_name = "python.exe"
                working_directory_marker = $script:BackendDirectory
                command_markers = @("-m uvicorn", "app.main:app", $script:BackendDirectory, "--port $($script:BackendPort)")
            }
        }
        "frontend" {
            return [pscustomobject]@{
                role = "frontend"
                port = $script:FrontendPort
                executable_path = $null
                executable_name = "node.exe"
                working_directory_marker = $script:FrontendDirectory
                command_markers = @($script:VitePath, "--port $($script:FrontendPort)", "--strictPort")
            }
        }
        default {
            throw "Unsupported process role in runtime metadata."
        }
    }
}

function New-OwnedProcessRecord {
    param(
        [string]$Role,
        [System.Diagnostics.Process]$Process
    )
    $identity = $null
    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    while ($null -eq $identity -and [DateTime]::UtcNow -lt $deadline) {
        $identity = Get-ProcessIdentity -ProcessId $Process.Id
        if ($null -eq $identity) {
            Start-Sleep -Milliseconds 100
        }
    }
    if ($null -eq $identity) {
        throw "Could not capture the $Role process identity."
    }
    $expected = Get-RoleExpectation -Role $Role
    return [pscustomobject]@{
        role = $expected.role
        launcher_pid = $identity.pid
        creation_time_utc = $identity.creation_time_utc
        executable_path = $identity.executable_path
        expected_port = $expected.port
        working_directory_marker = $expected.working_directory_marker
        command_markers = @($expected.command_markers)
        listener_pid = $null
        listener_creation_time_utc = $null
        listener_executable_path = $null
    }
}

function Assert-RunningState {
    param([object[]]$Records)
    $roles = @($Records | ForEach-Object { [string]$_.role })
    $backendCount = @($roles | Where-Object { $_ -ceq "backend" }).Count
    $frontendCount = @($roles | Where-Object { $_ -ceq "frontend" }).Count
    $hasExactlyRequiredRoles = (
        $Records.Count -eq 2 -and
        $backendCount -eq 1 -and
        $frontendCount -eq 1
    )
    if (-not $hasExactlyRequiredRoles) {
        throw "DEMO_RUNTIME_STATE_INCOMPLETE: RUNNING metadata must contain exactly one backend and one frontend record. Runtime metadata was retained. No process was terminated."
    }
}

function Assert-StartingState {
    param([object[]]$Records)
    $roles = @($Records | ForEach-Object { [string]$_.role })
    $backendCount = @($roles | Where-Object { $_ -ceq "backend" }).Count
    $frontendCount = @($roles | Where-Object { $_ -ceq "frontend" }).Count
    $isBackendOnly = $Records.Count -eq 1 -and $backendCount -eq 1
    $isCompleteLaunchSet = (
        $Records.Count -eq 2 -and
        $backendCount -eq 1 -and
        $frontendCount -eq 1
    )
    if (-not $isBackendOnly -and -not $isCompleteLaunchSet) {
        throw "DEMO_RUNTIME_STATE_INVALID: STARTING metadata must contain the backend record, optionally followed by one frontend record. Runtime metadata was retained. No process was terminated."
    }
}

function Assert-DemoStateStructure {
    param(
        [string]$Status,
        [object[]]$Records
    )
    if ($Status -eq "RUNNING") {
        Assert-RunningState -Records $Records
        return
    }
    if ($Status -eq "STARTING") {
        Assert-StartingState -Records $Records
        return
    }
    throw "Runtime metadata status is invalid. Runtime metadata was retained. No process was terminated."
}

function Save-DemoState {
    param(
        [string]$Status,
        [object[]]$Processes,
        [string]$SessionId,
        [string]$CreatedAtUtc
    )
    Assert-SafeRuntimePath
    Assert-DemoStateStructure -Status $Status -Records @($Processes)
    New-Item -ItemType Directory -Path $script:RuntimeDirectory -Force | Out-Null
    Assert-SafeRuntimePath
    $state = [ordered]@{
        schema_version = $script:StateSchemaVersion
        session_id = $SessionId
        status = $Status
        created_at_utc = $CreatedAtUtc
        repository_root = $script:RepositoryRoot
        processes = @($Processes)
    }
    $json = $state | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText(
        $script:StateTemporaryPath,
        $json,
        [Text.UTF8Encoding]::new($false)
    )
    Move-Item -LiteralPath $script:StateTemporaryPath -Destination $script:StatePath -Force
}

function Read-DemoState {
    Assert-SafeRuntimePath
    if (-not (Test-Path -LiteralPath $script:StatePath -PathType Leaf)) {
        return $null
    }
    try {
        $state = Get-Content -LiteralPath $script:StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "Runtime metadata is unreadable. No process was terminated."
    }
    if ([int]$state.schema_version -ne $script:StateSchemaVersion) {
        throw "Runtime metadata schema is unsupported. No process was terminated."
    }
    if (-not (Test-SamePath -Left ([string]$state.repository_root) -Right $script:RepositoryRoot)) {
        throw "Runtime metadata belongs to another repository. No process was terminated."
    }
    $status = [string]$state.status
    $records = @($state.processes)
    Assert-DemoStateStructure -Status $status -Records $records
    foreach ($record in $records) {
        $expected = Get-RoleExpectation -Role ([string]$record.role)
        if ([int]$record.expected_port -ne $expected.port) {
            throw "Runtime metadata port does not match its role. No process was terminated."
        }
        if (-not (Test-SamePath -Left ([string]$record.working_directory_marker) -Right $expected.working_directory_marker)) {
            throw "Runtime metadata working-directory marker is invalid. No process was terminated."
        }
    }
    return $state
}

function Confirm-OwnedProcess {
    param([object]$Record)
    $expected = Get-RoleExpectation -Role ([string]$Record.role)
    $processId = [int]$Record.launcher_pid
    $identity = Get-ProcessIdentity -ProcessId $processId
    if ($null -eq $identity) {
        return [pscustomobject]@{ status = "ABSENT"; reason = "process does not exist"; identity = $null }
    }
    if (-not (Test-SameCreationTime -Left $identity.creation_time_utc -Right $Record.creation_time_utc)) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "creation time does not match"; identity = $identity }
    }
    if (-not (Test-SamePath -Left $identity.executable_path -Right ([string]$Record.executable_path))) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "executable path does not match metadata"; identity = $identity }
    }
    if (-not [string]::Equals(
        [IO.Path]::GetFileName($identity.executable_path),
        $expected.executable_name,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "executable is not valid for the role"; identity = $identity }
    }
    if ($null -ne $expected.executable_path -and -not (Test-SamePath -Left $identity.executable_path -Right $expected.executable_path)) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "backend executable is outside the project virtual environment"; identity = $identity }
    }
    if (-not [string]::IsNullOrWhiteSpace($identity.command_line)) {
        foreach ($marker in $expected.command_markers) {
            if ($identity.command_line.IndexOf([string]$marker, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
                return [pscustomobject]@{ status = "MISMATCH"; reason = "command marker does not match the owned role"; identity = $identity }
            }
        }
    }
    return [pscustomobject]@{ status = "OWNED"; reason = "identity verified"; identity = $identity }
}

function Test-IdentityRoleMarkers {
    param(
        [object]$Identity,
        [object]$Expected
    )
    if (-not [string]::Equals(
        [IO.Path]::GetFileName($Identity.executable_path),
        $Expected.executable_name,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        return $false
    }
    if (-not [string]::IsNullOrWhiteSpace($Identity.command_line)) {
        foreach ($marker in $Expected.command_markers) {
            if ($Identity.command_line.IndexOf([string]$marker, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
                return $false
            }
        }
    }
    return $true
}

function Find-OwnedListenerIdentity {
    param([object]$Record)
    $expected = Get-RoleExpectation -Role ([string]$Record.role)
    foreach ($listenerId in @(Get-ListenerProcessIds -Port $expected.port)) {
        if (-not (Test-IsDescendantProcess -CandidateProcessId $listenerId -AncestorProcessId ([int]$Record.launcher_pid))) {
            continue
        }
        $identity = Get-ProcessIdentity -ProcessId $listenerId
        if ($null -ne $identity -and (Test-IdentityRoleMarkers -Identity $identity -Expected $expected)) {
            return $identity
        }
    }
    return $null
}

function Confirm-OwnedListener {
    param([object]$Record)
    if ($null -eq $Record.listener_pid -or [int]$Record.listener_pid -le 0) {
        return [pscustomobject]@{ status = "ABSENT"; reason = "listener identity was not recorded"; identity = $null }
    }
    $identity = Get-ProcessIdentity -ProcessId ([int]$Record.listener_pid)
    if ($null -eq $identity) {
        return [pscustomobject]@{ status = "ABSENT"; reason = "listener process does not exist"; identity = $null }
    }
    if (-not (Test-SameCreationTime -Left $identity.creation_time_utc -Right $Record.listener_creation_time_utc)) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "listener creation time does not match"; identity = $identity }
    }
    if (-not (Test-SamePath -Left $identity.executable_path -Right ([string]$Record.listener_executable_path))) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "listener executable path does not match"; identity = $identity }
    }
    $expected = Get-RoleExpectation -Role ([string]$Record.role)
    if (-not (Test-IdentityRoleMarkers -Identity $identity -Expected $expected)) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "listener command does not match the owned role"; identity = $identity }
    }
    $launcherIdentity = Get-ProcessIdentity -ProcessId ([int]$Record.launcher_pid)
    $recordedLauncherStillMatches = $null -ne $launcherIdentity -and
        (Test-SameCreationTime -Left $launcherIdentity.creation_time_utc -Right $Record.creation_time_utc) -and
        (Test-SamePath -Left $launcherIdentity.executable_path -Right ([string]$Record.executable_path))
    # CIM access may be denied even though Get-Process can safely verify the
    # recorded listener identity. Enforce ancestry whenever parent data is available;
    # otherwise do not turn an indeterminate tree lookup into a mismatch.
    $listenerParent = Get-CimInstance Win32_Process -Filter "ProcessId = $($identity.pid)" -ErrorAction SilentlyContinue
    if ($recordedLauncherStillMatches -and $null -ne $listenerParent -and
        -not (Test-IsDescendantProcess -CandidateProcessId $identity.pid -AncestorProcessId $launcherIdentity.pid)) {
        return [pscustomobject]@{ status = "MISMATCH"; reason = "listener is outside the recorded launcher tree"; identity = $identity }
    }
    return [pscustomobject]@{ status = "OWNED"; reason = "listener identity verified"; identity = $identity }
}

function Stop-ExactProcessTree {
    param([int]$ProcessId)
    & taskkill.exe /PID $ProcessId /T /F | Out-Null
    $taskkillCode = $LASTEXITCODE
    if ($taskkillCode -ne 0 -and (Test-ProcessExists -ProcessId $ProcessId)) {
        return $false
    }
    return $true
}

function Wait-ForOwnedShutdown {
    param([object[]]$Records)
    $deadline = [DateTime]::UtcNow.AddSeconds($script:StopTimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $processesGone = $true
        $ownedListenersGone = $true
        foreach ($record in $Records) {
            $recordPid = [int]$record.launcher_pid
            if (Test-ProcessExists -ProcessId $recordPid) {
                $processesGone = $false
            }
            $recordedProcessIds = @($recordPid)
            if ($null -ne $record.listener_pid -and [int]$record.listener_pid -gt 0) {
                $listenerPid = [int]$record.listener_pid
                $recordedProcessIds += $listenerPid
                if (Test-ProcessExists -ProcessId $listenerPid) {
                    $processesGone = $false
                }
            }
            foreach ($listenerOwner in @(Get-ListenerProcessIds -Port ([int]$record.expected_port))) {
                if ($recordedProcessIds -contains $listenerOwner) {
                    $ownedListenersGone = $false
                }
            }
        }
        if ($processesGone -and $ownedListenersGone) {
            return $true
        }
        Start-Sleep -Milliseconds 200
    }
    return $false
}

function Remove-FixedRuntimeState {
    Assert-SafeRuntimePath
    if (Test-Path -LiteralPath $script:StateTemporaryPath) {
        Remove-Item -LiteralPath $script:StateTemporaryPath -Force
    }
    if (Test-Path -LiteralPath $script:StatePath) {
        Remove-Item -LiteralPath $script:StatePath -Force
    }
}

function Stop-DemoSession {
    try {
        $state = Read-DemoState
    }
    catch {
        Write-DemoError $_.Exception.Message
        return $false
    }
    if ($null -eq $state) {
        Write-Host "No launcher-owned demo session is recorded. No process was stopped."
        foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
            if (@(Get-ListenerProcessIds -Port $port).Count -gt 0) {
                Write-Host "NOTICE: Port $port is occupied by an unowned process; it was not terminated."
            }
        }
        return $true
    }

    $records = @($state.processes)
    $checks = @()
    $listenerChecks = @()
    foreach ($record in $records) {
        $checks += Confirm-OwnedProcess -Record $record
        $listenerChecks += Confirm-OwnedListener -Record $record
    }
    # The venv Python launcher can hand off to an independently recorded listener and
    # then exit. Its PID may subsequently be reused. In that case, permit shutdown
    # only when the listener's recorded PID, creation time, executable and role all
    # still match; any listener mismatch remains fail-closed.
    $mismatchIndexes = @(0..($checks.Count - 1) | Where-Object {
        ($checks[$_].status -eq "MISMATCH" -and $listenerChecks[$_].status -ne "OWNED") -or
        $listenerChecks[$_].status -eq "MISMATCH"
    })
    if ($mismatchIndexes.Count -gt 0) {
        foreach ($index in $mismatchIndexes) {
            $reason = if ($checks[$index].status -eq "MISMATCH") { $checks[$index].reason } else { $listenerChecks[$index].reason }
            Write-DemoError "Refusing to stop $($records[$index].role) PID $($records[$index].launcher_pid): $reason."
        }
        Write-DemoError "Launcher ownership could not be established. Runtime metadata was retained."
        return $false
    }

    $stopFailed = $false
    for ($index = 0; $index -lt $records.Count; $index++) {
        $processIdToStop = $null
        if ($checks[$index].status -eq "OWNED") {
            $processIdToStop = [int]$records[$index].launcher_pid
        }
        elseif ($listenerChecks[$index].status -eq "OWNED") {
            $processIdToStop = [int]$records[$index].listener_pid
        }
        if ($null -ne $processIdToStop) {
            if (-not (Stop-ExactProcessTree -ProcessId $processIdToStop)) {
                Write-DemoError "The owned $($records[$index].role) process tree could not be terminated."
                $stopFailed = $true
            }
        }
    }
    if ($stopFailed -or -not (Wait-ForOwnedShutdown -Records $records)) {
        Write-DemoError "Verified shutdown did not complete within $($script:StopTimeoutSeconds) seconds. Runtime metadata was retained."
        return $false
    }

    if ([string]$state.status -eq "RUNNING") {
        $occupiedPorts = @(
            $script:RequiredRunningRoles | ForEach-Object {
                $expected = Get-RoleExpectation -Role $_
                if (@(Get-ListenerProcessIds -Port $expected.port).Count -gt 0) {
                    $expected.port
                }
            }
        )
        if ($occupiedPorts.Count -gt 0) {
            Write-DemoError "Verified process-tree shutdown completed, but required port(s) $($occupiedPorts -join ', ') remain occupied. Runtime metadata was retained and no port owner was terminated."
            return $false
        }
    }

    Remove-FixedRuntimeState
    if (@($checks | Where-Object { $_.status -eq "OWNED" }).Count -eq 0 -and
        @($listenerChecks | Where-Object { $_.status -eq "OWNED" }).Count -eq 0) {
        Write-Host "Stale launcher metadata was cleared; no recorded demo process was running."
    }
    elseif ([string]$state.status -eq "RUNNING") {
        Write-Host "Demo stopped: the launcher-owned backend and frontend process trees are gone."
    }
    else {
        Write-Host "Partial startup stopped: every recorded launcher-owned process tree is gone."
    }
    if ([string]$state.status -eq "STARTING") {
        foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
            if (@(Get-ListenerProcessIds -Port $port).Count -gt 0) {
                Write-Host "NOTICE: Port $port is occupied by an unowned process; it was not terminated."
            }
        }
    }
    return $true
}

function Get-CommandPath {
    param([string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return $null
    }
    return [IO.Path]::GetFullPath([string]$command.Source)
}

function Normalize-ChildProcessEnvironment {
    <#
    Windows environment variable names are case-insensitive, but a parent launched by
    another runtime can still contain both Path and PATH entries. Start-Process builds
    a case-insensitive child environment and rejects that collision. Normalize only
    this launcher process before creating children; the user's machine environment is
    never changed.
    #>
    $processEnvironment = [Environment]::GetEnvironmentVariables("Process")
    $pathEntries = @(
        $processEnvironment.Keys |
            Where-Object { [string]::Equals([string]$_, "PATH", [StringComparison]::OrdinalIgnoreCase) } |
            ForEach-Object { [pscustomobject]@{ key = [string]$_; value = [string]$processEnvironment[$_] } }
    )
    if ($pathEntries.Count -eq 0) {
        throw "PATH is not available for child-process startup."
    }

    # Prefer the longest inherited value when a malformed parent supplied duplicates;
    # this preserves the effective lookup path used by the lifecycle test harness.
    $effectivePath = ($pathEntries | Sort-Object { $_.value.Length } -Descending | Select-Object -First 1).value
    foreach ($entry in $pathEntries) {
        [Environment]::SetEnvironmentVariable($entry.key, $null, "Process")
    }
    [Environment]::SetEnvironmentVariable("PATH", $effectivePath, "Process")
}

function Get-MajorMinorVersion {
    param([string]$Output, [string]$Label)
    $match = [regex]::Match($Output, "(?<major>\d+)\.(?<minor>\d+)")
    if (-not $match.Success) {
        throw "$Label version output could not be parsed."
    }
    return [pscustomobject]@{
        major = [int]$match.Groups["major"].Value
        minor = [int]$match.Groups["minor"].Value
        display = $match.Value
    }
}

function Invoke-StartupPreflight {
    if (-not (Test-Path -LiteralPath $script:PythonPath -PathType Leaf)) {
        throw "Python virtual environment is missing. Follow docs\demo\DEMO_RUNBOOK.md first."
    }
    $pythonVersionText = (& $script:PythonPath --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "The project Python executable could not be run."
    }
    $pythonVersion = Get-MajorMinorVersion -Output $pythonVersionText -Label "Python"
    if ($pythonVersion.major -ne 3 -or $pythonVersion.minor -lt 12) {
        throw "Python 3.12 or newer within major version 3 is required; found $pythonVersionText."
    }

    $nodePath = Get-CommandPath -Name "node.exe"
    if ($null -eq $nodePath) {
        throw "node.exe is not available on PATH. Install Node.js 22 or newer."
    }
    $nodeVersionText = (& $nodePath --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Node.js could not be run."
    }
    $nodeVersion = Get-MajorMinorVersion -Output $nodeVersionText -Label "Node.js"
    if ($nodeVersion.major -lt 22) {
        throw "Node.js 22 or newer is required; found $nodeVersionText."
    }

    $npmPath = Get-CommandPath -Name "npm.cmd"
    if ($null -eq $npmPath) {
        throw "npm.cmd is not available on PATH. Install npm 10 or newer."
    }
    $npmVersionText = (& $npmPath --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "npm could not be run."
    }
    $npmVersion = Get-MajorMinorVersion -Output $npmVersionText -Label "npm"
    if ($npmVersion.major -lt 10) {
        throw "npm 10 or newer is required; found $npmVersionText."
    }

    if (-not (Test-Path -LiteralPath $script:VitePath -PathType Leaf)) {
        throw "Frontend dependencies are missing. Run npm ci in apps\frontend."
    }
    & $script:PythonPath -c "import fastapi, pydantic, pydantic_settings, uvicorn" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependencies are incomplete. Install apps\backend[dev] in the project virtual environment."
    }
    Push-Location $script:FrontendDirectory
    try {
        & $npmPath ls --depth=0 --silent 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend dependencies are inconsistent. Run npm ci in apps\frontend."
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "Preflight: Python $($pythonVersion.display), Node.js $($nodeVersion.display), npm $($npmVersion.display); backend/frontend dependencies available."
    return [pscustomobject]@{ node_path = $nodePath; npm_path = $npmPath }
}

function Test-DemoEndpoint {
    param([string]$Uri)
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
        return [int]$response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Wait-DemoHealthy {
    param([object[]]$Records)
    $backendRecord = $Records | Where-Object { $_.role -eq "backend" } | Select-Object -First 1
    $frontendRecord = $Records | Where-Object { $_.role -eq "frontend" } | Select-Object -First 1
    $deadline = [DateTime]::UtcNow.AddSeconds($script:HealthTimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (-not (Test-ProcessExists -ProcessId ([int]$backendRecord.launcher_pid)) -or
            -not (Test-ProcessExists -ProcessId ([int]$frontendRecord.launcher_pid))) {
            return $false
        }
        $backendListener = Find-OwnedListenerIdentity -Record $backendRecord
        $frontendListener = Find-OwnedListenerIdentity -Record $frontendRecord
        if ($null -ne $backendListener -and $null -ne $frontendListener -and
            (Test-DemoEndpoint -Uri "http://127.0.0.1:$($script:BackendPort)/health") -and
            (Test-DemoEndpoint -Uri "http://127.0.0.1:$($script:FrontendPort)/")) {
            $backendRecord.listener_pid = $backendListener.pid
            $backendRecord.listener_creation_time_utc = $backendListener.creation_time_utc
            $backendRecord.listener_executable_path = $backendListener.executable_path
            $frontendRecord.listener_pid = $frontendListener.pid
            $frontendRecord.listener_creation_time_utc = $frontendListener.creation_time_utc
            $frontendRecord.listener_executable_path = $frontendListener.executable_path
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Start-DemoSession {
    if (Test-Path -LiteralPath $script:StatePath) {
        Write-DemoError "Launcher runtime metadata already exists. Run scripts\stop_demo_windows.bat; ownership will be checked before any process is stopped."
        return $false
    }
    foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
        if (-not (Test-PortAvailable -Port $port)) {
            Write-DemoError "Required port $port is occupied. Startup was aborted; the occupant was not terminated."
            return $false
        }
    }

    try {
        $preflight = Invoke-StartupPreflight
    }
    catch {
        Write-DemoError $_.Exception.Message
        return $false
    }

    New-Item -ItemType Directory -Path $script:RuntimeDirectory -Force | Out-Null
    $sessionId = [Guid]::NewGuid().ToString("D")
    $createdAtUtc = [DateTime]::UtcNow.ToString("O")
    $backendOut = Join-Path $script:RuntimeDirectory "backend-$sessionId.out.log"
    $backendErr = Join-Path $script:RuntimeDirectory "backend-$sessionId.err.log"
    $frontendOut = Join-Path $script:RuntimeDirectory "frontend-$sessionId.out.log"
    $frontendErr = Join-Path $script:RuntimeDirectory "frontend-$sessionId.err.log"
    $startedProcesses = @()
    $records = @()
    $startupStage = "backend launch"

    try {
        Normalize-ChildProcessEnvironment
        $env:APP_ENV = "development"
        $env:ACRA_CONNECTOR_MODE = "mock"
        $env:GOLDTIER_CONNECTOR_MODE = "mock"
        $env:IDP_CONNECTOR_MODE = "local_pdf_text"
        $env:OWNERSHIP_CONNECTOR_MODE = "mock"
        $env:DEMO_CONTROLS_ENABLED = "true"
        $backendArguments = @(
            "-m", "uvicorn", "app.main:app",
            "--app-dir", $script:BackendDirectory,
            "--host", "127.0.0.1",
            "--port", [string]$script:BackendPort
        )
        $backendProcess = Start-Process -FilePath $script:PythonPath -ArgumentList $backendArguments `
            -WorkingDirectory $script:RepositoryRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr
        $startedProcesses += $backendProcess
        $startupStage = "backend identity capture"
        $records += New-OwnedProcessRecord -Role "backend" -Process $backendProcess

        $env:VITE_DEMO_CONTROLS_ENABLED = "true"
        $startupStage = "frontend launch"
        $frontendArguments = @(
            $script:VitePath,
            "--host", "127.0.0.1",
            "--port", [string]$script:FrontendPort,
            "--strictPort"
        )
        $frontendProcess = Start-Process -FilePath $preflight.node_path -ArgumentList $frontendArguments `
            -WorkingDirectory $script:FrontendDirectory -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr
        $startedProcesses += $frontendProcess
        $startupStage = "frontend identity capture"
        $records += New-OwnedProcessRecord -Role "frontend" -Process $frontendProcess

        $startupStage = "runtime metadata write"
        Save-DemoState -Status "STARTING" -Processes $records -SessionId $sessionId -CreatedAtUtc $createdAtUtc
        $startupStage = "health verification"
        if (-not (Wait-DemoHealthy -Records $records)) {
            throw "Backend/frontend health did not become ready within $($script:HealthTimeoutSeconds) seconds."
        }
        Save-DemoState -Status "RUNNING" -Processes $records -SessionId $sessionId -CreatedAtUtc $createdAtUtc
    }
    catch {
        Write-DemoError "$startupStage failed: $($_.Exception.Message)"
        $cleanupFailed = $false
        if (Test-Path -LiteralPath $script:StatePath) {
            try {
                if (-not (Stop-DemoSession)) {
                    $cleanupFailed = $true
                }
            }
            catch {
                $cleanupFailed = $true
            }
        }
        else {
            $recordedIds = @($records | ForEach-Object { [int]$_.launcher_pid })
            foreach ($record in $records) {
                $ownership = Confirm-OwnedProcess -Record $record
                if ($ownership.status -eq "OWNED") {
                    if (-not (Stop-ExactProcessTree -ProcessId ([int]$record.launcher_pid))) {
                        $cleanupFailed = $true
                    }
                }
                elseif ($ownership.status -eq "MISMATCH") {
                    $cleanupFailed = $true
                }
            }
            foreach ($process in $startedProcesses) {
                if ($recordedIds -notcontains $process.Id -and (Test-ProcessExists -ProcessId $process.Id)) {
                    Write-DemoError "PID $($process.Id) was created by this invocation but its ownership identity could not be captured; it was not terminated blindly."
                    $cleanupFailed = $true
                }
            }
            if ($records.Count -gt 0 -and -not (Wait-ForOwnedShutdown -Records $records)) {
                $cleanupFailed = $true
            }
            if (-not $cleanupFailed) {
                Remove-FixedRuntimeState
            }
        }
        if ($cleanupFailed) {
            if (Test-Path -LiteralPath $script:StatePath) {
                Write-DemoError "Startup failed and exact-process cleanup was incomplete. Use the retained metadata with stop_demo_windows.bat."
            }
            else {
                Write-DemoError "Startup failed and ownership-safe cleanup was incomplete. Inspect the reported exact PID; no process was terminated without verified ownership."
            }
        }
        else {
            Write-Host "Startup failed; every process created by this invocation was cleaned up."
        }
        return $false
    }

    Write-Host "Demo started and verified healthy."
    Write-Host "Backend: http://127.0.0.1:$($script:BackendPort)/health"
    Write-Host "Frontend: http://127.0.0.1:$($script:FrontendPort)"
    Write-Host "Mode: ACRA MOCK, IDP LOCAL_PDF_TEXT (Local POC), Ownership MOCK, GoldTier MOCK"
    Write-Host "Runtime metadata: .runtime\demo-processes.json (process-management fields only; Git-ignored)"
    return $true
}

function Show-DemoStatus {
    $state = Read-DemoState
    if ($null -eq $state) {
        Write-Host "No launcher-owned demo session is recorded."
        return $true
    }
    $allOwned = $true
    foreach ($record in @($state.processes)) {
        $check = Confirm-OwnedProcess -Record $record
        Write-Host "$($record.role): PID $($record.launcher_pid) - $($check.status)"
        if ($check.status -ne "OWNED") {
            $allOwned = $false
        }
    }
    return $allOwned
}

try {
    switch ($Action) {
        "Start" {
            if (-not (Start-DemoSession)) { exit 1 }
            exit 0
        }
        "Stop" {
            if (-not (Stop-DemoSession)) { exit 1 }
            exit 0
        }
        "Reset" {
            Write-Host "Resetting process-local synthetic state through verified stop then verified start."
            if (-not (Stop-DemoSession)) {
                Write-DemoError "Reset aborted because verified stop failed. No start was attempted."
                exit 1
            }
            if (-not (Start-DemoSession)) {
                Write-DemoError "Reset failed because the fresh demo did not start healthy."
                exit 1
            }
            Write-Host "Demo reset verified: fresh backend/frontend processes are healthy."
            exit 0
        }
        "Status" {
            if (-not (Show-DemoStatus)) { exit 1 }
            exit 0
        }
    }
}
catch {
    Write-DemoError $_.Exception.Message
    exit 1
}
