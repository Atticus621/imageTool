---
description: Kill all Python processes, clear ROI cache, and relaunch the ROI GUI. Use after code changes to ensure clean state.
agent: main
---

# Kill + Restart ROI GUI

Run these steps in order:

1. Clear Python cache directories:
```powershell
Remove-Item "C:\Users\user\Documents\imageTools\test\roi\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\user\Documents\imageTools\test\roi\shapes\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\user\Documents\imageTools\test\roi\interactions\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
```

2. Kill all running Python processes:
```powershell
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
```

3. Launch the ROI GUI:
```powershell
Start-Process -FilePath "C:\Users\user\miniconda3\envs\claude-imagetool\python.exe" -ArgumentList "C:\Users\user\Documents\imageTools\test\roi\main.py" -WorkingDirectory "C:\Users\user\Documents\imageTools"
```

4. Wait 3 seconds for GUI to initialize, then optionally send a test command via TCP to verify:
```powershell
Start-Sleep -Seconds 3
C:\Users\user\miniconda3\envs\claude-imagetool\python.exe -c "import socket,json;s=socket.socket();s.connect(('127.0.0.1',9527));s.send(json.dumps({'command':'get_canvas_info'}).encode());print(s.recv(4096).decode());s.close()"
```

Report: whether the GUI launched successfully and the TCP connection test result.
