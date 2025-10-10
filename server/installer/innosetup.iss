[Setup]
AppName=Restormer Remote AI Denoise Server
AppVersion=1.0.0
DefaultDirName={pf}\\RestormerServer
DefaultGroupName=Restormer Server
OutputDir=dist
OutputBaseFilename=RestormerServerInstaller
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source="..\\dist\\RestormerServer.exe"; DestDir="{app}"; Flags: ignoreversion
Source="..\\.env.example"; DestDir="{app}"; Flags: onlyifdoesntexist

[Icons]
Name="{group}\\Restormer Server"; Filename="{app}\\RestormerServer.exe"
Name="{commondesktop}\\Restormer Server"; Filename="{app}\\RestormerServer.exe"; Tasks: desktopicon

[Tasks]
Name=desktopicon; Description="Create a &desktop icon"; GroupDescription="Additional icons:"; Flags: checkedonce

[Run]
Filename="{app}\\RestormerServer.exe"; Description="Launch Restormer Server"; Flags: nowait postinstall skipifsilent
