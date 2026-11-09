; Inno Setup 6 — compilare con:  iscc build\installer.iss
#define AppName "Transcriptor"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6B1E2F0C-8C1A-4C55-9C3B-7D2E5A1F9A01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=Transcriptor-Setup-{#AppVersion}
Compression=lzma2/normal
SolidCompression=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
WizardStyle=modern
UninstallDisplayIcon={app}\Transcriptor.exe

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Transcriptor\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\models\faster-whisper-medium\*"; DestDir: "{app}\models\faster-whisper-medium"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Transcriptor.exe"
Name: "{group}\Disinstalla {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Transcriptor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Transcriptor.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
