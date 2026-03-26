; Inno Setup 6 用（Windows）
; 事前にプロジェクトルートで PyInstaller を実行し dist\BasketballGM.exe を生成してからコンパイルしてください。
;   pip install -r requirements-dev.txt
;   python -m PyInstaller --noconfirm BasketballGM.spec
; コンパイル例（パスは環境に合わせて変更）:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\BasketballGM.iss
;
; ソースファイルが無い場合、コンパイル時にエラーになります（実行時チェック不要）。
;
; コード署名（Authenticode）:
; - 手軽な流れ: 先に dist\BasketballGM.exe を署名 → 本スクリプトで Inno ビルド → 生成された
;   dist\BasketballGM_Setup_*.exe に再度署名（installer\sign_windows_release.ps1）。
; - Inno 組み込みでコンパイル時署名する場合は [Setup] に SignTool= を追加し、
;   Inno の「Signing」設定と signtool のパスを合わせる（公式ドキュメント参照）。

#define MyAppName "国内バスケ GM"
#define MyAppVersion "0.1.0"
#define MyAppExeName "BasketballGM.exe"
#define MyAppPublisher "basketball_project"
#define MyAppSource "..\\dist\\BasketballGM.exe"

[Setup]
AppId={{C4A91E03-8B2F-4D6A-9E1C-7F305B2A8D41}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\BasketballGM
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=BasketballGM_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupLogging=yes

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加のショートカット:"; Flags: unchecked

[Files]
Source: "{#MyAppSource}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\ユーザーデータフォルダを開く (.basketball_sim)"; Filename: "{win}\explorer.exe"; Parameters: "%USERPROFILE%\.basketball_sim"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "インストール後にゲームを起動する"; Flags: nowait postinstall skipifsilent
