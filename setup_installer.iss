; Network Automation v7.0 Inno Setup Script
; UTF-8 BOM encoded

#define MyAppName "Network Automation"
#define MyAppVersion "7.0"
#define MyAppPublisher "Your Company"
#define MyAppExeName "NetworkAutomation.exe"
#define MyAppURL "https://auto-network.co.kr"

[Setup]
; Basic Info
AppId={{8F9A2E4B-7D3C-4A6F-9B1E-5C8D2F4A3E6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\NetworkAutomation
DefaultGroupName={#MyAppName}
OutputDir=.
OutputBaseFilename=NetworkAutomation_v7.0_Setup
SetupIconFile=icons\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
DisableWelcomePage=no

; Language
ShowLanguageDialog=no

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a Quick Launch shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\NetworkAutomation\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\NetworkAutomation\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('Network Automation v7.0 installation completed!' #13#10#13#10 +
           'Thank you for using Network Automation.', mbInformation, MB_OK);
  end;
end;
