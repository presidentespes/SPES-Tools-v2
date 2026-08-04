#define MyAppName "SPES Tools"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SPES Mestre Ginnastica A.S.D."
#define MyAppExeName "SPES_Tools.exe"

[Setup]
AppId={{A93D8B37-878C-4A4A-90CF-8D714866D13B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SPES Tools
DefaultGroupName={#MyAppName}
OutputDir=..\installer_output
OutputBaseFilename=Setup_SPES_Tools
SetupIconFile=..\assets\Spes.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\SPES_Tools.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\SPES Tools"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\SPES Tools"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Disinstalla SPES Tools"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia SPES Tools"; Flags: nowait postinstall skipifsilent
