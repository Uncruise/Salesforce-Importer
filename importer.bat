@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Check if location is cloud then skip client import sync
IF "%IMPORT_LOCATION%" == "-location Cloud" (
    goto skip_import_directory_check
)

REM Using ! instead of % in case using special chars like parenthesis in path
IF "!IMPORT_DIRECTORY!" == "" (
    goto skip_import_directory_check
)

IF NOT EXIST "!IMPORT_DIRECTORY!" (
    cscript importer.vbs "Error Import Directory does not exist: !IMPORT_DIRECTORY!"
    goto scriptexit
)

REM Backward Compatibility: Try with and wihout quotes in case they are already included
echo ***** Copy Incoming *****
xcopy "!IMPORT_DIRECTORY!" "%IMPORTER_DIRECTORY%\%CLIENT_TYPE%\Incoming" /s /y /i

if NOT EXIST "%IMPORTER_DIRECTORY%\%CLIENT_TYPE%\Incoming" (
    echo ***** Copy Incoming without quotes *****
    xcopy !IMPORT_DIRECTORY! %IMPORTER_DIRECTORY%\%CLIENT_TYPE%\Incoming /s /y /i
)

:skip_import_directory_check

echo ***** Python Setup Check *****
IF "%PATH:~0,11%" == "%PYTHON_HOME:~0,11%" (
    goto skip_python_path
)

echo Update Path for Python
set PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%JAVA_HOME%;%PATH%

:skip_python_path

cd "%PYTHON_HOME%"

REM python -m pip install --upgrade pip

REM pip uninstall -y pypiwin32
REM pip install --upgrade pypiwin32

REM pip uninstall -y pywin32
REM pip install pywin32==223

REM pip install simple_salesforce==0.75.3

echo ***** Authentication Setup *****
copy /Y "%IMPORTER_PRIVATE_DIR%\DataLoader\key.txt" "%IMPORTER_DIRECTORY%\%CLIENT_TYPE%\DataLoader\key.txt"

echo ***************
IF "%IMPORT_ENVIRONMENT%" == "Sandbox" (
    echo *****Sandbox Data Import Automation
    python "%IMPORTER_DIRECTORY%\..\importer_sandbox.py" %IMPORT_ENVIRONMENT% %CLIENT_TYPE% %IMPORT_MODE% %EMAIL_LIST% %IMPORT_WAITTIME% %IMPORT_NOREFRESH% %IMPORT_NOUPDATE% %IMPORT_ENABLEDELETE% %IMPORT_NOEXPORTODBC% %IMPORT_NOEXPORTSF% %IMPORT_INSERTATTEMPTS% %IMPORT_EMAILATTACHMENTS% %IMPORT_INTERACTIVEMODE% %IMPORT_DISPLAYALERTS% %IMPORT_LOCATION%
) else (
    echo *****Production Data Import Automation
    python "%IMPORTER_DIRECTORY%\..\importer.py" %IMPORT_ENVIRONMENT% %CLIENT_TYPE% %IMPORT_MODE% %EMAIL_LIST% %IMPORT_WAITTIME% %IMPORT_NOREFRESH% %IMPORT_NOUPDATE% %IMPORT_ENABLEDELETE% %IMPORT_NOEXPORTODBC% %IMPORT_NOEXPORTSF% %IMPORT_INSERTATTEMPTS% %IMPORT_EMAILATTACHMENTS% %IMPORT_INTERACTIVEMODE% %IMPORT_DISPLAYALERTS% %IMPORT_LOCATION%
)
echo ***************

cd %IMPORTER_PRIVATE_DIR%

:scriptexit

ENDLOCAL