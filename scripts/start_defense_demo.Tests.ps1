<#
Pruebas Pester focalizadas de scripts/start_defense_demo.ps1 (PR #229,
corrección de arranque combinado / gestión de procesos). Escritas para
Pester 3.4.0 (el disponible en esta máquina vía Windows PowerShell 5.1 /
módulo integrado) -- sintaxis "Should Be" sin guion, compatible también
con Pester 4/5 en modo de compatibilidad heredada.

No dependen de red externa. Las pruebas de arranque/parada real de
servicios (backend/frontend) están en el ensayo manual documentado en
docs/design/defense-demo-startup-guide.md, no acá: estas pruebas cubren
específicamente los cinco criterios exigidos por el encargo:

  1. Puerto ocupado o duplicado -> no inicia ningún proceso.
  2. Fallo/timeout de un servicio -> revierte lo creado por esa invocación.
  3. PID reutilizado con identidad distinta -> no se detiene.
  4. Segunda ejecución de -Stop -> operación segura (idempotente).
  5. Asignación correcta de las dos URLs de frontend por modo.
#>

$scriptPath = Join-Path $PSScriptRoot 'start_defense_demo.ps1'
# Dot-source: por el guard `if ($MyInvocation.InvocationName -eq '.') { return }`
# del propio script, esto carga todas las funciones sin arrancar ningún
# proceso ni exigir -Mode/-Stop.
. $scriptPath -Stop 2>$null

$runDir = Join-Path (Split-Path $PSScriptRoot -Parent) '.defense-demo-run'
$registryPath = Join-Path $runDir 'registry.json'

function Backup-RealRegistry {
    if (Test-Path $registryPath) {
        Copy-Item $registryPath "$registryPath.pester-backup" -Force
    }
}
function Restore-RealRegistry {
    if (Test-Path "$registryPath.pester-backup") {
        Move-Item "$registryPath.pester-backup" $registryPath -Force
    } elseif (Test-Path $registryPath) {
        Remove-Item $registryPath -Force
    }
}

Describe 'Resolve-FrontendBaseUrls (asignación de las dos URLs por modo)' {
    It '-Mode all separa API_BASE_URL (LabPort) de PRODUCER_API_BASE_URL (ProducerPort)' {
        $result = Resolve-FrontendBaseUrls -Mode 'all' -ProducerPort 8199 -LabPort 8299 -NeedsProducer $true -NeedsLab $true
        $result.ApiBaseUrl | Should Be 'http://127.0.0.1:8299'
        $result.ProducerApiBaseUrl | Should Be 'http://127.0.0.1:8199'
        $result.ApiBaseUrl | Should Not Be $result.ProducerApiBaseUrl
    }

    It '-Mode sensor-lab asigna ambas URLs al LabPort' {
        $result = Resolve-FrontendBaseUrls -Mode 'sensor-lab' -ProducerPort 8199 -LabPort 8299 -NeedsProducer $false -NeedsLab $true
        $result.ApiBaseUrl | Should Be 'http://127.0.0.1:8299'
        $result.ProducerApiBaseUrl | Should Be 'http://127.0.0.1:8299'
    }

    It '-Mode pergamino asigna ambas URLs al ProducerPort' {
        $result = Resolve-FrontendBaseUrls -Mode 'pergamino' -ProducerPort 8199 -LabPort 8299 -NeedsProducer $true -NeedsLab $false
        $result.ApiBaseUrl | Should Be 'http://127.0.0.1:8199'
        $result.ProducerApiBaseUrl | Should Be 'http://127.0.0.1:8199'
    }

    It '-Mode melchor-romero asigna ambas URLs al ProducerPort' {
        $result = Resolve-FrontendBaseUrls -Mode 'melchor-romero' -ProducerPort 8199 -LabPort 8299 -NeedsProducer $true -NeedsLab $false
        $result.ApiBaseUrl | Should Be 'http://127.0.0.1:8199'
        $result.ProducerApiBaseUrl | Should Be 'http://127.0.0.1:8199'
    }
}

Describe 'Test-PortAssignment (puerto ocupado o duplicado -> no arranca nada)' {
    It 'lanza excepción con puertos duplicados entre servicios' {
        $ports = New-Object System.Collections.Generic.List[object]
        $ports.Add(@{ name = '-LabPort'; value = 8299 }) | Out-Null
        $ports.Add(@{ name = '-FrontendPort'; value = 8299 }) | Out-Null
        { Test-PortAssignment -portsToUse $ports } | Should Throw 'duplicados'
    }

    It 'lanza excepción con un puerto fuera de rango (>65535)' {
        $ports = New-Object System.Collections.Generic.List[object]
        $ports.Add(@{ name = '-LabPort'; value = 70000 }) | Out-Null
        { Test-PortAssignment -portsToUse $ports } | Should Throw 'fuera de rango'
    }

    It 'lanza excepción con un puerto fuera de rango (<1)' {
        $ports = New-Object System.Collections.Generic.List[object]
        $ports.Add(@{ name = '-LabPort'; value = 0 }) | Out-Null
        { Test-PortAssignment -portsToUse $ports } | Should Throw 'fuera de rango'
    }

    It 'lanza excepción cuando el puerto ya está escuchando, y no toca puertos libres' {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
        $listener.Start()
        $occupiedPort = $listener.LocalEndpoint.Port
        try {
            $ports = New-Object System.Collections.Generic.List[object]
            $ports.Add(@{ name = '-LabPort'; value = $occupiedPort }) | Out-Null
            { Test-PortAssignment -portsToUse $ports } | Should Throw 'ya está en uso'
        } finally {
            $listener.Stop()
        }
    }

    It 'no lanza excepción cuando todos los puertos están libres y son distintos' {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
        $listener.Start()
        $freePort = $listener.LocalEndpoint.Port
        $listener.Stop()
        Start-Sleep -Milliseconds 200
        $ports = New-Object System.Collections.Generic.List[object]
        $ports.Add(@{ name = '-LabPort'; value = $freePort }) | Out-Null
        { Test-PortAssignment -portsToUse $ports } | Should Not Throw
    }
}

Describe 'Test-IdentityMatches (identidad de proceso, no solo PID)' {
    It 'coincide cuando CreationTime (normalizado a UTC) y ExecutablePath son iguales' {
        $recorded = [pscustomobject]@{ CreationTime = [datetime]'2026-01-01T12:00:00Z'; ExecutablePath = 'C:\a\b.exe' }
        $current = [pscustomobject]@{ CreationTime = [datetime]'2026-01-01T12:00:00Z'; ExecutablePath = 'C:\a\b.exe' }
        Test-IdentityMatches -recorded $recorded -current $current | Should Be $true
    }

    It 'NO coincide cuando el ExecutablePath difiere (PID reciclado por otro proceso)' {
        $recorded = [pscustomobject]@{ CreationTime = [datetime]'2026-01-01T12:00:00Z'; ExecutablePath = 'C:\a\b.exe' }
        $current = [pscustomobject]@{ CreationTime = [datetime]'2026-01-01T12:00:00Z'; ExecutablePath = 'C:\other\process.exe' }
        Test-IdentityMatches -recorded $recorded -current $current | Should Be $false
    }

    It 'NO coincide cuando el proceso ya no existe ($current = $null)' {
        $recorded = [pscustomobject]@{ CreationTime = [datetime]'2026-01-01T12:00:00Z'; ExecutablePath = 'C:\a\b.exe' }
        Test-IdentityMatches -recorded $recorded -current $null | Should Be $false
    }

    It 'coincide pese al desfase Utc-vs-Local del mismo instante (hallazgo del ensayo real de esta tarea)' {
        # Reproduce exactamente el bug encontrado: ConvertFrom-Json produce
        # Kind=Utc, Get-CimInstance produce Kind=Local -- ambos representan
        # el mismo instante real.
        $instant = Get-Date
        $recordedUtc = $instant.ToUniversalTime()
        $currentLocal = $instant.ToLocalTime()
        $recordedUtc.Kind | Should Be ([System.DateTimeKind]::Utc)
        $recorded = [pscustomobject]@{ CreationTime = $recordedUtc; ExecutablePath = 'C:\a\b.exe' }
        $current = [pscustomobject]@{ CreationTime = $currentLocal; ExecutablePath = 'C:\a\b.exe' }
        Test-IdentityMatches -recorded $recorded -current $current | Should Be $true
    }
}

Describe 'Stop-TrackedProcesses (PID reutilizado, idempotencia, sin terminación global)' {
    BeforeEach {
        Backup-RealRegistry
        if (Test-Path $registryPath) { Remove-Item $registryPath -Force }
    }
    AfterEach {
        if (Test-Path $registryPath) { Remove-Item $registryPath -Force -ErrorAction SilentlyContinue }
        Restore-RealRegistry
    }

    It 'PID existente pero con identidad distinta a la registrada: no lo detiene' {
        # Proceso real de prueba (dummy), con identidad real capturada.
        $dummy = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile', '-Command', 'Start-Sleep -Seconds 30' -PassThru -WindowStyle Hidden
        try {
            Start-Sleep -Milliseconds 300
            # Se registra una identidad DELIBERADAMENTE distinta a la real
            # de este PID (ejecutable falso, fecha de creación falsa) --
            # simula un PID reciclado por otro proceso desde que se grabó
            # el registro.
            $fakeEntry = [pscustomobject]@{
                service        = 'test_dummy'
                pid            = $dummy.Id
                creationTime   = [datetime]'2000-01-01T00:00:00Z'
                executablePath = 'C:\no\existe\otro.exe'
                runId          = 'test-run-id'
                logBase        = (Join-Path $runDir 'test_dummy')
            }
            New-Item -ItemType Directory -Path $runDir -Force | Out-Null
            (@($fakeEntry) | ConvertTo-Json -Depth 5) | Set-Content -Path $registryPath -Encoding UTF8

            Stop-TrackedProcesses

            (Get-Process -Id $dummy.Id -ErrorAction SilentlyContinue) | Should Not Be $null
        } finally {
            Stop-Process -Id $dummy.Id -Force -ErrorAction SilentlyContinue
        }
    }

    It 'rollback (Stop-TrackedProcesses -OnlyThisRun) detiene el proceso propio ya arrancado ante el fallo de un servicio posterior, y deja intacto un proceso ajeno' {
        # Arranca un proceso propio real y lo registra EXACTAMENTE como lo
        # haría el flujo real (Add-TrackedProcess, mismo $runId del
        # dot-source de este archivo) -- representa un servicio que ya
        # arrancó con éxito (p. ej. el backend productor en -Mode all).
        $ownProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile', '-Command', 'Start-Sleep -Seconds 30' -PassThru -WindowStyle Hidden
        # Proceso AJENO real: nunca se registra con Add-TrackedProcess, no
        # pertenece a esta ejecución -- simula un proceso de otra sesión
        # de verificación corriendo en la misma máquina.
        $foreignProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile', '-Command', 'Start-Sleep -Seconds 30' -PassThru -WindowStyle Hidden
        try {
            Start-Sleep -Milliseconds 300
            Add-TrackedProcess -service 'own_first_service' -processId $ownProcess.Id -logBase (Join-Path $runDir 'own_first_service') | Out-Null

            # "Provocar el fallo de un servicio posterior": se simula el
            # mismo patrón try/catch que usa el flujo real del script
            # (sección final del propio start_defense_demo.ps1) -- un
            # segundo servicio falla después de que el primero ya está
            # registrado, y el bloque catch invoca el rollback real.
            $rollbackRan = $false
            try {
                throw "fallo simulado de un servicio posterior (p. ej. el backend del laboratorio no respondió)"
            } catch {
                Stop-TrackedProcesses -OnlyThisRun
                $rollbackRan = $true
            }
            $rollbackRan | Should Be $true

            # El proceso propio (servicio "posterior" simulado aparte) fue
            # detenido por el rollback.
            (Get-Process -Id $ownProcess.Id -ErrorAction SilentlyContinue) | Should Be $null
            # El proceso AJENO, nunca registrado bajo este runId, permanece
            # intacto -- el rollback nunca hace una terminación global.
            (Get-Process -Id $foreignProcess.Id -ErrorAction SilentlyContinue) | Should Not Be $null
        } finally {
            Stop-Process -Id $ownProcess.Id -Force -ErrorAction SilentlyContinue
            Stop-Process -Id $foreignProcess.Id -Force -ErrorAction SilentlyContinue
        }
    }

    It 'segunda ejecución de -Stop es segura (idempotente, no lanza error) cuando no hay nada que detener' {
        if (Test-Path $registryPath) { Remove-Item $registryPath -Force }
        { Stop-TrackedProcesses } | Should Not Throw
        { Stop-TrackedProcesses } | Should Not Throw
    }

    It 'con registry.json vacío ([]) no lanza error' {
        New-Item -ItemType Directory -Path $runDir -Force | Out-Null
        '[]' | Set-Content -Path $registryPath -Encoding UTF8
        { Stop-TrackedProcesses } | Should Not Throw
    }

    It 'archivos .pid heredados (sin identidad) no se usan para detener nada' {
        if (Test-Path $registryPath) { Remove-Item $registryPath -Force }
        $legacyPidFile = Join-Path $runDir 'legacy_pester_test.pid'
        New-Item -ItemType Directory -Path $runDir -Force | Out-Null
        '999999' | Set-Content -Path $legacyPidFile -Encoding UTF8
        try {
            { Stop-TrackedProcesses } | Should Not Throw
        } finally {
            Remove-Item $legacyPidFile -Force -ErrorAction SilentlyContinue
        }
    }
}

Describe 'Arranque real: fallo/timeout de un servicio revierte lo creado (integración)' {
    # Requiere un intérprete Python real disponible; se salta si no hay
    # ninguno resoluble, en vez de fingir un resultado. Permite
    # $env:PESTER_PYTHON_EXE para máquinas donde "python" no está en PATH
    # (verificado que es el caso en esta máquina de desarrollo).
    $pythonExe = if ($env:PESTER_PYTHON_EXE) { $env:PESTER_PYTHON_EXE } else { 'python' }
    $pythonAvailable = $false
    try {
        & $pythonExe --version 2>&1 | Out-Null
        $pythonAvailable = ($LASTEXITCODE -eq 0)
    } catch { $pythonAvailable = $false }

    It 'Pergamino con DataDir/BundleRoot vacíos falla y no deja el backend escuchando' -Skip:(-not $pythonAvailable) {
        Backup-RealRegistry
        try {
            $emptyDataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("pester-empty-data-" + [guid]::NewGuid().ToString('N'))
            $emptyBundleRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("pester-empty-bundle-" + [guid]::NewGuid().ToString('N'))
            New-Item -ItemType Directory -Path $emptyDataDir -Force | Out-Null
            New-Item -ItemType Directory -Path $emptyBundleRoot -Force | Out-Null
            $testPort = 18199
            try {
                & $scriptPath -Mode pergamino -DataDir $emptyDataDir -BundleRoot $emptyBundleRoot `
                    -PythonExe $pythonExe -ProducerPort $testPort -SkipFrontend -ReadyTimeoutSeconds 15 2>&1 | Out-Null
                $threw = $false
            } catch {
                $threw = $true
            }
            $threw | Should Be $true
            Start-Sleep -Milliseconds 500
            $listening = Get-NetTCPConnection -LocalPort $testPort -State Listen -ErrorAction SilentlyContinue
            $listening | Should Be $null
        } finally {
            Restore-RealRegistry
        }
    }
}
