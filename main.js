const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

let mainWindow;
let pythonProcess;

function waitForFlask(callback, tries = 0) {
   http.get('http://localhost:5000', (res) => {
       if (res.statusCode === 200) {
           callback();
       }
   }).on('error', (err) => {
       if (tries < 30) {
           setTimeout(() => waitForFlask(callback, tries + 1), 1000);
       }
   });
}

function getAppPath() {
    return app.isPackaged 
        ? path.join(app.getAppPath(), '..', 'app.asar.unpacked')
        : __dirname;
}

async function checkFirstRun() {
   const appPath = getAppPath();
   console.log('Checking first run in:', appPath);
   if (!fs.existsSync(path.join(appPath, '.env'))) {
       return new Promise((resolve, reject) => {
           const setupPath = path.join(appPath, 'setup.sh');
           console.log('Running setup from:', setupPath);
           const setup = spawn('bash', [setupPath], {
               stdio: 'inherit',
               cwd: appPath
           });
           setup.on('close', (code) => {
               if (code === 0) resolve();
               else reject(new Error('Setup failed'));
           });
       });
   }
}

function startPythonBackend() {
    const appPath = getAppPath();
    console.log('Starting Python from:', appPath);
    
    const venvPath = path.join(appPath, 'venv');
    const pythonPath = path.join(venvPath, 'bin', 'python3');
    const flaskAppPath = path.join(appPath, 'app.py');

    console.log('Python path:', pythonPath);
    console.log('Flask app path:', flaskAppPath);

    try {
        pythonProcess = spawn(pythonPath, [flaskAppPath], {
            stdio: 'inherit',
            cwd: appPath,
            env: {
                ...process.env,
                VIRTUAL_ENV: venvPath,
                PATH: `${path.dirname(pythonPath)}:${process.env.PATH}`
            }
        });

        pythonProcess.on('error', (err) => {
            console.error('Python process error:', err);
        });

    } catch (error) {
        console.error('Failed to start Python process:', error);
        throw error;
    }
}

function createWindow() {
   mainWindow = new BrowserWindow({
       width: 1200,
       height: 800,
       backgroundColor: '#1e1e2e', 
       icon: path.join(getAppPath(), 'templates', 'images', 'ntepd.png'),
       webPreferences: {
           nodeIntegration: true,
           contextIsolation: false
       }
   });

   mainWindow.setMenu(null);

   waitForFlask(() => {
       mainWindow.loadURL('http://localhost:5000');
   });

   mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
       console.error('Page failed to load:', errorDescription);
   });
}

app.whenReady().then(async () => {
   try {
       await checkFirstRun();
       startPythonBackend();
       createWindow();
   } catch (error) {
       console.error('Startup error:', error);
       app.quit();
   }
});

app.on('window-all-closed', () => {
   if (pythonProcess) {
       pythonProcess.kill();
   }
   app.quit();
});

process.on('uncaughtException', (err) => {
   console.error('Uncaught exception:', err);
});