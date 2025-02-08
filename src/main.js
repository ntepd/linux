const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    // Start Python backend
    const pythonPath = app.isPackaged
        ? path.join(process.resourcesPath, 'backend', 'app.py')
        : path.join(__dirname, 'backend', 'app.py');
    
    pythonProcess = spawn('python3', [pythonPath]);
    
    // Wait for Flask to start
    setTimeout(() => {
        mainWindow.loadURL('http://localhost:3547');
    }, 1000);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});