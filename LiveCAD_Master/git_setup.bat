@echo off
setlocal
echo [INFO] Setting up Git...
set /p REPO=Enter Repository URL (or empty to skip): 
if not exist .git ( git init & git branch -M main )
git add .
git commit -m 'LiveCAD Master Build'
if not "%REPO%"=="" (
    git remote remove origin 2>nul
    git remote add origin %REPO%
    git push -u origin main
)
echo [SUCCESS] Git operations finished.
pause