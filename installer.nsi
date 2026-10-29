Unicode True
!include "MUI2.nsh"
!include "x64.nsh"
Name "IEC104 Reader"
OutFile "dist/IEC104-Reader-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\IEC104-Reader"
InstallDirRegKey HKCU "Software\TheBam1990\IEC104-Reader" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
VIProductVersion "1.5.2.0"
VIAddVersionKey /LANG=1031 "ProductName" "IEC104 Reader"
VIAddVersionKey /LANG=1031 "FileDescription" "IEC104 Reader Installation"
VIAddVersionKey /LANG=1031 "FileVersion" "1.5.2.0"
VIAddVersionKey /LANG=1031 "LegalCopyright" "TheBam1990"
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "German"
Function .onInit
 ${IfNot} ${RunningX64}
  MessageBox MB_ICONSTOP "Dieses Programm benoetigt Windows mit 64 Bit."
  Abort
 ${EndIf}
FunctionEnd
Section "IEC104 Reader"
 SetOutPath "$INSTDIR"
 File /r "dist/IEC104-Reader/*"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 CreateShortcut "$SMPROGRAMS\IEC104 Reader.lnk" "$INSTDIR\IEC104-Reader.exe"
 CreateShortcut "$DESKTOP\IEC104 Reader.lnk" "$INSTDIR\IEC104-Reader.exe"
 WriteRegStr HKCU "Software\TheBam1990\IEC104-Reader" "InstallDir" "$INSTDIR"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "DisplayName" "IEC104 Reader"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "DisplayVersion" "1.5.2"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "Publisher" "TheBam1990"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "DisplayIcon" "$INSTDIR\IEC104-Reader.exe"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "UninstallString" '"$INSTDIR\Uninstall.exe"'
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "NoModify" 1
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader" "NoRepair" 1
SectionEnd
Section "Uninstall"
 Delete "$SMPROGRAMS\IEC104 Reader.lnk"
 Delete "$DESKTOP\IEC104 Reader.lnk"
 Delete "$INSTDIR\IEC104-Reader.exe"
 Delete "$INSTDIR\README.md"
 Delete "$INSTDIR\LICENSE"
 Delete "$INSTDIR\BUILD-INFO.json"
 Delete "$INSTDIR\SHA256SUMS.txt"
 RMDir /r "$INSTDIR\_internal"
 RMDir /r "$INSTDIR\docs"
 Delete "$INSTDIR\Uninstall.exe"
 RMDir "$INSTDIR"
 DeleteRegKey HKCU "Software\TheBam1990\IEC104-Reader"
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\IEC104-Reader"
SectionEnd
