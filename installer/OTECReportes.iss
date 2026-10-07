; Inno Setup script. Build the folder version first:  .\build.ps1 -Installer
; Installs per user (no administrator rights needed) and creates Start menu / desktop shortcuts.
#define AppName "OTEC Reportes"
#define AppVersion "1.0.0"

[Setup]
AppId={{6B1F3E2A-8C4D-4E7B-9A21-0F3C5D7E9B11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=OTEC Impronta
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=Instalar OTEC Reportes {#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppName}.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
