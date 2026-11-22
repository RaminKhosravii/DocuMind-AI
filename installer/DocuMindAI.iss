#ifndef AppVersion
  #define AppVersion "0.1.2"
#endif

#define AppName "DocuMind AI"
#define AppPublisher "DocuMind AI"
#define AppExeName "DocuMindAI.exe"

[Setup]
AppId={{B8C01D5C-9D55-4B2A-A1D2-6A4D8E12A901}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\DocuMind AI
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=DocuMindAI-Setup-{#AppVersion}
SetupIconFile=..\assets\documind.ico
UninstallDisplayIcon={app}\DocuMindAI.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\DocuMindAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DocuMind AI"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\_internal\assets\documind.ico"
Name: "{autodesktop}\DocuMind AI"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\_internal\assets\documind.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch DocuMind AI"; Flags: nowait postinstall skipifsilent
