; Inno Setup Script for the N Compiler
#define MyAppName "N Compiler"
#define MyAppVersion "0.0.1"
#define MyAppPublisher "N Team"
#define MyAppExeName "nc.exe"

[Setup]
AppId={{D1A2B3C4-E5F6-4A7B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName=C:\NC
DefaultGroupName={#MyAppName}
OutputDir=.
OutputBaseFilename=n_compiler_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes

[Files]
Source: "nc.exe"; DestDir: "{app}\bin"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};C:\NC\bin"; \
    Check: NeedsAddPath('C:\NC\bin')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  { check if path already exists }
  Result := Pos(Uppercase(Param), Uppercase(OrigPath)) = 0;
end;

