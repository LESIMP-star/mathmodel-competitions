@echo off
REM ============================================================================
REM  build_paper.bat -- 干净重编译论文
REM  每次改动 tex 后跑本脚本：先删掉所有生成物（只保留 *.tex 与 figures/），
REM  再用 xelatex 连跑两遍。可避免残留 .aux / .toc 被截断导致的乱码与假错误。
REM  用法：双击，或在命令行 build_paper.bat
REM ============================================================================
setlocal
cd /d "%~dp0"

set XELATEX=D:\textline\texlive\2026\bin\windows\xelatex.exe
if not exist "%XELATEX%" (
  echo [ERROR] 找不到 xelatex: %XELATEX%
  exit /b 1
)

echo [1/3] 删除所有生成物（保留 .tex 与 figures\）...
for %%f in (main.aux main.log main.out main.toc main.pdf main.synctex.gz main.lof main.lot) do (
  if exist "%%f" del /q "%%f"
)
if exist sections\*.aux del /q sections\*.aux
if exist "..\latex模板\log" rmdir /s /q "..\latex模板\log" 2>nul

echo [2/3] 第一遍编译...
"%XELATEX%" -interaction=nonstopmode -halt-on-error main.tex > nul 2>&1
if errorlevel 1 (
  echo [ERROR] 第一遍编译失败，请查看 main.log
  exit /b 1
)

echo [3/3] 第二遍编译（生成目录与总页数）...
"%XELATEX%" -interaction=nonstopmode -halt-on-error main.tex > nul 2>&1
if errorlevel 1 (
  echo [ERROR] 第二遍编译失败，请查看 main.log
  exit /b 1
)

echo.
echo ===== 完成 =====
findstr /c:"Output written on main.pdf" main.log
findstr /c:"! " main.log > nul && echo [WARN] 日志中仍有以 "! " 开头的行，请检查 main.log
echo 生成物：main.pdf
endlocal
