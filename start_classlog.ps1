$ProjectDir = "C:\Users\seewo\Desktop\课堂管理程序"
$PythonExe = "C:\Users\seewo\AppData\Local\Programs\Python\Python313\python.exe"
$Script = "run.py"
$proc = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -like "*$Script*" }
if (-not $proc) {
    Write-Output "ClassLog not running, starting..."
    Start-Process -FilePath $PythonExe -ArgumentList $Script -WorkingDirectory $ProjectDir -WindowStyle Hidden
} else {
    Write-Output "ClassLog is already running, skipping."
}