const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const kill = require('tree-kill');

let mainWindow = null;
let splashWindow = null;
let pyProcess = null;
let backendSpawned = false;

function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 450,
        height: 300,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    splashWindow.loadFile(path.join(__dirname, '..', 'frontend', 'splash.html'));
    splashWindow.on('closed', () => (splashWindow = null));
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 950,
        minHeight: 650,
        frame: false, // Frameless window
        show: false, // Don't show immediately
        backgroundColor: '#0c0c0e', // Premium dark mode background
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    // Automatically approve microphone media permissions
    mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
        if (permission === 'media' || permission === 'audioCapture') {
            callback(true);
        } else {
            callback(false);
        }
    });

    // Redirect renderer console messages to terminal output for debugging
    mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
        console.log(`[Renderer Console]: ${message} (Line: ${line})`);
    });

    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'index.html'));

    mainWindow.once('ready-to-show', () => {
        if (splashWindow) {
            splashWindow.close();
        }
        mainWindow.show();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// Check if FastAPI is running
function checkBackendStatus(callback) {
    const options = {
        hostname: '127.0.0.1',
        port: 8000,
        path: '/api/status',
        method: 'GET',
        timeout: 800
    };

    const req = http.request(options, (res) => {
        if (res.statusCode === 200) {
            callback(true);
        } else {
            callback(false);
        }
    });

    req.on('error', () => {
        callback(false);
    });

    req.on('timeout', () => {
        req.destroy();
        callback(false);
    });

    req.end();
}

// Spawn FastAPI backend
function spawnBackend() {
    if (backendSpawned) return;
    backendSpawned = true;

    const backendPath = path.join(__dirname, '..', 'backend', 'app.py');
    console.log(`Spawning backend: python "${backendPath}"`);

    // Inject PYTHONPATH to ensure the root directory is searched for imports
    const spawnEnv = Object.assign({}, process.env, {
        PYTHONPATH: path.join(__dirname, '..')
    });

    // Wrap script path in double quotes to handle spaces in folder names
    pyProcess = spawn('python', [`"${backendPath}"`], { shell: true, env: spawnEnv });

    pyProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data}`);
    });

    pyProcess.stderr.on('data', (data) => {
        console.error(`[Python Err]: ${data}`);
    });

    pyProcess.on('close', (code) => {
        console.log(`Python backend exited with code ${code}`);
        pyProcess = null;
        backendSpawned = false;
    });
}

// Poll backend and transition to main window when ready
function pollBackendAndStart(retries = 0, maxRetries = 20) {
    checkBackendStatus((isRunning) => {
        if (isRunning) {
            console.log('Backend is running. Launching main window...');
            createMainWindow();
        } else {
            if (retries === 0) {
                // First failure, try spawning the backend
                spawnBackend();
            }

            if (retries < maxRetries) {
                console.log(`Waiting for backend... Retry ${retries + 1}/${maxRetries}`);
                setTimeout(() => pollBackendAndStart(retries + 1, maxRetries), 1000);
            } else {
                console.error('FastAPI backend failed to start. Launching main window anyway...');
                createMainWindow();
            }
        }
    });
}

app.on('ready', () => {
    createSplashWindow();
    // Start polling the backend after a brief delay
    setTimeout(() => pollBackendAndStart(), 500);
});

// IPC handlers for Frameless window controls
ipcMain.on('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
    if (mainWindow) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    }
});

ipcMain.on('window-close', () => {
    if (mainWindow) mainWindow.close();
});

// IPC handler to open URL in standard browser
ipcMain.on('open-external', (event, url) => {
    if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
        shell.openExternal(url);
    }
});

// IPC handler to select a directory natively
ipcMain.handle('select-directory', async () => {
    const { dialog } = require('electron');
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Attach Local Directory to ArCh',
        properties: ['openDirectory']
    });
    if (result.canceled) {
        return null;
    } else {
        return result.filePaths[0];
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    if (pyProcess) {
        console.log('Terminating Python backend process tree...');
        // kill process tree dynamically using tree-kill
        kill(pyProcess.pid, 'SIGTERM', (err) => {
            if (err) {
                console.error('Error killing Python process tree:', err);
            } else {
                console.log('Python process tree killed successfully.');
            }
        });
    }
});
