pyinstaller ^
  --onefile ^
  --add-binary "nettool.exe;." ^
  --add-data "icon.ico;." ^
  --add-data "icon.png;." ^
  --add-data "icon_small.png;." ^
  --add-data "azure.tcl;." ^
  --add-data "theme;theme" ^
  --name=RakurakuNS-Plus ^
  --icon=icon_small.ico ^
  main.py
