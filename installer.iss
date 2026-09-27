; 光标管家 - Inno Setup 安装脚本
; 编译: ISCC.exe installer.iss
; 产物: dist\光标管家_setup.exe

#define MyAppName "光标管家"
#define MyAppNameEn "CursorButler"
#define MyAppVersion "1.1.3"
#define MyAppPublisher "yunxiuyunju-bit"
#define MyAppURL "https://github.com/yunxiuyunju-bit/cursor-butler"
#define MyAppExeName "光标管家.exe"

[Setup]
AppId={{8F3A2C41-7B6E-4D92-A5C8-1E9F0D3B6A72}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; 装到用户目录，免管理员权限
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=光标管家_setup
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 中文放第一位，作为默认语言（安装界面直接显示中文）
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 只在 Win10+ 上安装
MinVersion=10.0

[Languages]
Name: "chinese"; MessagesFile: "installer_lang\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
chinese.CreateLib=正在准备主题库目录...
chinese.LaunchApp=立即运行 {#MyAppName}
chinese.OpenLib=打开主题库文件夹（把主题放进去）
chinese.AdditionalIcons=创建桌面快捷方式
chinese.ReadmeNote={#MyAppName} 不附带任何光标主题。%n%n请把你下载的主题（.zip 或解压后的文件夹）放进主题库目录，程序会自动识别。%n%n主题库位置：%n%1
english.CreateLib=Preparing theme library...
english.LaunchApp=Run {#MyAppName} now
english.OpenLib=Open the theme library folder
english.AdditionalIcons=Create a desktop shortcut
english.ReadmeNote={#MyAppName} ships with no cursor themes.%n%nPut the themes you downloaded (.zip or extracted folders) into the theme library; the app detects them automatically.%n%nTheme library: %n%1

[Tasks]
Name: "desktopicon"; Description: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
; 预建空主题库 + 安装包目录，方便用户直接丢 zip 进去
Source: "_empty_theme_lib\*"; DestDir: "{app}\光标主题\安装包"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; 主题库目录（用户放主题的地方）
Name: "{app}\光标主题"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\主题库文件夹"; Filename: "{app}\光标主题"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完先打开主题库文件夹，让用户知道主题该放哪
Filename: "{app}\光标主题"; Description: "{cm:OpenLib}"; Flags: nowait postinstall shellexec skipifsilent
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
procedure InitializeWizard();
begin
  { 安装开始时提示主题库位置 }
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { 确保主题库目录存在 }
    ForceDirectories(ExpandConstant('{app}\光标主题'));
    ForceDirectories(ExpandConstant('{app}\光标主题\安装包'));
  end;
end;

[UninstallDelete]
; 卸载时清理程序生成的配置与缓存（不动用户放的主题）
Type: files; Name: "{app}\光标主题\config.json"
Type: filesandordirs; Name: "{app}\__pycache__"
