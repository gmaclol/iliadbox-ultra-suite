@echo off
setlocal enabledelayedexpansion
title "Iliadbox Ultra Suite"
color 0B

echo.
echo ===================================================================
echo   ___ _ _           _ _                 ____      _               
echo  ^|_ _^| ^(_^)__ _  __^| ^| ^|__   _____  __  / ___^|   ^| ^|__   ___ _ __ 
echo   ^| ^| ^| ^|/ _` ^|/ _` ^| '_ \ / _ \ \/ / ^| ^|       ^| '_ \ / _ \ '__^|
echo   ^| ^| ^| ^| (_^| ^| (_^| ^| ^|_) ^| (_) ^>  ^<  ^| ^|___ _  ^| ^|_) ^|  __/ ^|   
echo  ^|___^|_^|_^|\__,_^|\__,_^|_.__/ \___/_/\_\  \____^(_^) ^|_.__/ \___^|_^|   
echo.
echo                 ULTRA SUITE WI-FI 7 / WI-FI 6
echo ===================================================================
echo.

:: 1. Check Python installation if exe not present
if not exist "Iliadbox.exe" (
    where python >nul 2>nul
    if !errorlevel! neq 0 (
        color 0C
        echo [ERRORE] Python non trovato nel sistema e Iliadbox.exe non presente!
        echo Installa Python da https://python.org o dal Microsoft Store.
        echo Assicurati di spuntare "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
    echo [1/3] Verifica ambiente Python completata.
) else (
    echo [1/3] Eseguibile autonomo Iliadbox.exe pronto.
)

:: 2. Check and discover free TCP port
echo [2/3] Scansione porte TCP libere in corso...
set TARGET_PORT=0
for %%P in (8080 8081 8082 8888 5000 3000 9000 9090 7777) do (
    netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul 2>nul
    if !errorlevel! neq 0 (
        if !TARGET_PORT! equ 0 (
            set TARGET_PORT=%%P
        )
    )
)

if !TARGET_PORT! equ 0 (
    echo [PORTA] Tutte le porte predefinite sono occupate.
    echo [PORTA] Richiesta al sistema operativo di inventare una porta libera...
    for /f "usebackq tokens=*" %%I in (`powershell -NoProfile -Command "$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0); $l.Start(); $p = $l.LocalEndpoint.Port; $l.Stop(); Write-Output $p"`) do set TARGET_PORT=%%I
    echo [PORTA] Porta libera inventata con successo: !TARGET_PORT!
) else (
    echo [PORTA] Porta libera di default identificata con successo: !TARGET_PORT!
)

:: 3. Launch the Application
echo [3/3] Avvio dell'applicazione desktop su porta !TARGET_PORT!...
echo.

if exist "Iliadbox.exe" (
    echo [START] Avvio di Iliadbox.exe (server autonomo + interfaccia grafica)...
    start "" "Iliadbox.exe" !TARGET_PORT!
    exit /b 0
)

echo -------------------------------------------------------------------
echo   DASHBOARD DISPONIBILE SU: http://127.0.0.1:!TARGET_PORT!
echo   (Premi CTRL+C in questa finestra per arrestare il server)
echo -------------------------------------------------------------------
echo.

:: Run app_desktop.py passing the chosen port
python app_desktop.py !TARGET_PORT!

pause
