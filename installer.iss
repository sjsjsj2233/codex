; Network Automation Installer Script
; Inno Setup 6.x

#define MyAppName      "Network Automation"
#define MyAppVersion   "8.0"
#define MyAppPublisher "김상준"
#define MyAppURL       "https://auto-network.co.kr"
#define MyAppExeName   "NetworkAutomation.exe"
#define MyAppIcon      "icons\app_icon.ico"

[Setup]
AppId={{B7F2A3C1-4D8E-4F9A-B2C3-D4E5F6A7B8C9}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=NetworkAutomation_Setup_v{#MyAppVersion}
SetupIconFile={#MyAppIcon}
LicenseFile=license.txt
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=6.1sp1
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 설치 마법사 이미지 (선택)
; WizardImageFile=icons\banner.jpg

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "dist\NetworkAutomation\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\NetworkAutomation\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";                          Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";                    Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Network Automation v8.0 설치 마법사에 오신 것을 환영합니다.' + #13#10 + #13#10 +
    '이 프로그램은 네트워크 장비 자동화를 위한 도구입니다.' + #13#10 + #13#10 +
    '계속하려면 [다음]을 클릭하십시오.';
end;
