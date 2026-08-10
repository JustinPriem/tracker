; Inno Setup Skript fuer Repxo.
; Baut einen einzelnen Setup.exe-Installer aus dem PyInstaller-Onedir-Build
; (dist\Repxo\), damit Nutzer nur eine Datei herunterladen/ausfuehren
; muessen statt einen Ordner (exe + _internal) manuell zu entpacken.
;
; Bauen:
;   "C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\repxo.iss
;
; Voraussetzung: dist\Repxo\ muss vorher per PyInstaller gebaut sein
; (siehe README.md, Abschnitt "Als eigenstaendige .exe bauen").

#define MyAppName "Repxo"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Justin Priem"
#define MyAppExeName "Repxo.exe"
#define MyAppURL "https://github.com/JustinPriem/tracker"

[Setup]
; Fest vergebene AppId, NICHT aendern - sonst erkennt Windows Updates nicht
; als Update der bestehenden Installation.
AppId={{9A5DC83B-CC13-453A-9414-8745BF03DCA0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation pro Benutzer unter %LOCALAPPDATA%\Programs\Repxo - kein
; Admin/UAC-Prompt noetig (gleiches Prinzip wie VS Code, Discord, Slack).
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

OutputDir=..\dist_installer
OutputBaseFilename=Repxo-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Repxo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
