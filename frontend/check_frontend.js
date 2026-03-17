const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

const FRONTEND_PORT = process.env.FRONTEND_PORT || '3000';
const BACKEND_PORT = process.env.BACKEND_PORT || '8000';
const START_SERVERS = process.env.START_SERVERS === 'true';
const KEEP_RUNNING = process.env.KEEP_RUNNING === 'true';
const BACKEND_ENV = {
    ...process.env,
    DISABLE_LIVE_FETCH: process.env.DISABLE_LIVE_FETCH || 'true',
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || '',
};

(async () => {
    const url = process.argv[2] || `http://localhost:${FRONTEND_PORT}`;
    console.log(`Checking ${url}...`);

    let backendProc = null;
    let frontendProc = null;

    const waitForPort = (port, host = '127.0.0.1', timeoutMs = 60000) => new Promise((resolve, reject) => {
        const start = Date.now();
        const check = () => {
            const socket = new net.Socket();
            socket.setTimeout(2000);
            socket.once('error', () => {
                socket.destroy();
                if (Date.now() - start > timeoutMs) {
                    reject(new Error(`Timeout waiting for ${host}:${port}`));
                } else {
                    setTimeout(check, 500);
                }
            });
            socket.once('timeout', () => {
                socket.destroy();
                if (Date.now() - start > timeoutMs) {
                    reject(new Error(`Timeout waiting for ${host}:${port}`));
                } else {
                    setTimeout(check, 500);
                }
            });
            socket.connect(port, host, () => {
                socket.end();
                resolve();
            });
        };
        check();
    });

    const startBackend = () => {
        const cwd = path.resolve(__dirname, '..', 'backend');
        const python = path.join(cwd, '.venv', 'bin', 'uvicorn');
        backendProc = spawn(
            python,
            ['app.main:app', '--host', '0.0.0.0', '--port', BACKEND_PORT],
            { cwd, env: BACKEND_ENV, stdio: 'pipe' }
        );
        backendProc.stdout.on('data', d => process.stdout.write(d));
        backendProc.stderr.on('data', d => process.stderr.write(d));
    };

    const startFrontend = () => {
        const cwd = path.resolve(__dirname);
        frontendProc = spawn(
            'npm',
            ['run', 'dev', '--', '--port', FRONTEND_PORT],
            { cwd, stdio: 'pipe' }
        );
        frontendProc.stdout.on('data', d => process.stdout.write(d));
        frontendProc.stderr.on('data', d => process.stderr.write(d));
    };

    const cleanup = () => {
        if (frontendProc) frontendProc.kill('SIGINT');
        if (backendProc) backendProc.kill('SIGINT');
    };

    process.on('exit', cleanup);
    process.on('SIGINT', () => { cleanup(); process.exit(1); });
    process.on('SIGTERM', () => { cleanup(); process.exit(1); });

    if (START_SERVERS) {
        console.log('Starting backend + frontend...');
        startBackend();
        startFrontend();
    }

    try {
        await waitForPort(BACKEND_PORT);
        await waitForPort(FRONTEND_PORT);
    } catch (err) {
        console.error('Server readiness check failed:', err.message);
        cleanup();
        process.exit(1);
    }

    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();

    const errors = [];
    const warnings = [];

    page.on('console', msg => {
        if (msg.type() === 'error') {
            errors.push(msg.text());
        } else if (msg.type() === 'warning') {
            warnings.push(msg.text());
        }
    });
    page.on('pageerror', error => {
        errors.push(error.message);
    });

    try {
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
        console.log("Page loaded successfully.");
    } catch (err) {
        console.error("Failed to load page:", err.message);
        await browser.close();
        if (!KEEP_RUNNING) {
            cleanup();
        }
        process.exit(1);
    }

    // Basic UI assertions
    const title = await page.title();
    if (!title || !title.toLowerCase().includes('bobfrmmktg')) {
        errors.push(`Unexpected page title: ${title}`);
    }

    const h1 = await page.$eval('h1', el => el.textContent?.trim() || '').catch(() => '');
    if (!h1 || !h1.toLowerCase().includes('marketing performance')) {
        errors.push(`Expected header not found. Found: "${h1}"`);
    }

    const hasReportCards = await page.$$eval('.card', els => els.length).catch(() => 0);
    if (hasReportCards === 0) {
        const emptyState = await page.$$eval('div', els => els.some(e => (e.textContent || '').includes('No historical reports found.'))).catch(() => false);
        if (emptyState) {
            errors.push('No reports displayed. Empty state shown.');
        } else {
            errors.push('No report cards rendered and no empty state detected.');
        }
    }

    await browser.close();
    if (!KEEP_RUNNING) {
        cleanup();
    }

    if (errors.length > 0) {
        console.error('\n❌ Found ' + errors.length + ' Errors:');
        errors.forEach((err, i) => console.error(`  ${i + 1}. ${err}`));
        process.exit(1);
    } else {
        console.log('\n✅ UI checks passed.');
        if (warnings.length > 0) {
            console.log(`\n(There were ${warnings.length} warnings)`);
            warnings.forEach((w, i) => console.log(`  ${i + 1}. ${w}`));
        }
    }

    if (KEEP_RUNNING) {
        console.log('\nServers are still running. Press Ctrl+C to stop.');
        setInterval(() => {}, 1 << 30);
    }
})();
