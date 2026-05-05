@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║       Gerando ValidadorSIGNO.exe (PyInstaller)       ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: Garante que as dependências estão instaladas
echo [1/4] Verificando dependências...
python -m pip install customtkinter pyinstaller pandas openpyxl --quiet
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependências. Verifique o Python e o pip.
    pause
    exit /b 1
)
echo        OK

:: Remove build anterior
echo [2/4] Limpando builds anteriores...
if exist "dist\ValidadorSIGNO.exe" del /f /q "dist\ValidadorSIGNO.exe"
if exist "build" rmdir /s /q "build"
echo        OK

:: Descobre onde o customtkinter está instalado
echo [3/4] Localizando customtkinter...
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i
echo        Path: %CTK_PATH%

:: Roda o PyInstaller
echo [4/4] Compilando o executável...
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "ValidadorSIGNO" ^
    --icon "validador_signo.ico" ^
    --add-data "manuais;manuais" ^
    --add-data "exemplos;exemplos" ^
    --add-data "%CTK_PATH%;customtkinter" ^
    --hidden-import "customtkinter" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "pandas" ^
    --hidden-import "openpyxl" ^
    --hidden-import "validador_signo" ^
    --collect-all "customtkinter" ^
    validador_gui.py

if errorlevel 1 (
    echo.
    echo ╔══════════════════════════════════════════╗
    echo ║  ERRO: Falha na compilação. Veja acima.  ║
    echo ╚══════════════════════════════════════════╝
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  SUCESSO! Executável gerado em:                      ║
echo ║  dist\ValidadorSIGNO.exe                             ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo Deseja abrir a pasta dist\ agora? [S/N]
set /p resp=
if /i "%resp%"=="S" explorer dist
pause
