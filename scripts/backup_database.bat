@echo off
REM Database Backup Script for Music Legends Bot (Windows)
REM Uses PostgreSQL client tools for creating backups

setlocal enabledelayedexpansion

REM Configuration
if "%DB_NAME%"=="" set DB_NAME=music_legends
if "%DB_HOST%"=="" set DB_HOST=localhost
if "%DB_PORT%"=="" set DB_PORT=5432
if "%DB_USER%"=="" set DB_USER=postgres
if "%BACKUP_DIR%"=="" set BACKUP_DIR=C:\backups\music_legends

REM Create timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,8%_%dt:~8,6%"
set "BACKUP_FILE=%BACKUP_DIR%\music_legends_backup_%TIMESTAMP%.sql"

REM Create backup directory if it doesn't exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo 🗄️ Starting database backup...
echo 📅 Timestamp: %TIMESTAMP%
echo 📁 Backup file: %BACKUP_FILE%

REM Check if PostgreSQL tools are available
pg_dump --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: pg_dump not found. PostgreSQL client tools not installed.
    echo Please install PostgreSQL from postgresql.org with Command Line Tools
    pause
    exit /b 1
)

REM Test database connection
echo 🔗 Testing database connection...
pg_isready -h %DB_HOST% -p %DB_PORT% -U %DB_USER% >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Cannot connect to database at %DB_HOST%:%DB_PORT%
    pause
    exit /b 1
)

REM Create the backup
echo 💾 Creating database backup...
set PGPASSWORD=%DB_PASSWORD%
pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% > "%BACKUP_FILE%"
if errorlevel 1 (
    echo ❌ Error: Backup creation failed
    pause
    exit /b 1
)

echo ✅ Backup created successfully!

REM Get backup size
for %%F in ("%BACKUP_FILE%") do set "size=%%~zF"
set /a "size_mb=%size%/1048576"
echo 📊 Backup size: %size_mb% MB

REM Compress the backup
echo 🗜️ Compressing backup...
powershell -Command "Compress-Archive -Path '%BACKUP_FILE%' -DestinationPath '%BACKUP_FILE%.zip' -Force"
del "%BACKUP_FILE%"
set "COMPRESSED_FILE=%BACKUP_FILE%.zip"
echo ✅ Backup compressed: %COMPRESSED_FILE%

REM Get compressed size
for %%F in ("%COMPRESSED_FILE%") do set "compressed_size=%%~zF"
set /a "compressed_size_mb=%compressed_size%/1048576"
echo 📊 Compressed size: %compressed_size_mb% MB

REM Clean up old backups (keep last 7 days)
echo 🧹 Cleaning up old backups...
forfiles /p "%BACKUP_DIR%" /m "music_legends_backup_*.zip" /d -7 /c "cmd /c del @path"
echo ✅ Old backups cleaned up

echo 🎉 Backup completed successfully!
echo 📍 Location: %COMPRESSED_FILE%

pause
