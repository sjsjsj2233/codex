; Network Automation Installer Script
; Inno Setup 6.x

#define MyAppName "Network Automation"
#define MyAppVersion "6.0"
#define MyAppPublisher "Your Company Name"
#define MyAppExeName "NetworkAutomation.exe"
#define MyAppIcon "icons\app_icon.ico"

[Setup]
; 기본 설정
AppId={{Network-Automation-v6}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=NetworkAutomation_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; 아이콘 설정
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}

; 권한 설정
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Windows 버전
MinVersion=6.1sp1

; 아키텍처
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 모든 파일 포함
Source: "dist_temp\NetworkAutomation\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist_temp\NetworkAutomation\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 시작 메뉴 바로가기
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; 바탕화면 바로가기
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 설치 완료 후 실행 옵션
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 한국어 커스텀 메시지
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Network Automation 설치 마법사에 오신 것을 환영합니다.' + #13#10 + #13#10 +
    '이 프로그램은 네트워크 장비 자동화를 위한 도구입니다.' + #13#10 +
    '계속하려면 [다음]을 클릭하십시오.';
end;
