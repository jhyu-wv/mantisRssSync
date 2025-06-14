class Logger {
    static info(message, data = null) {
        console.log(`[INFO] ${new Date().toISOString()} - ${message}`);
        if (data) console.log(JSON.stringify(data, null, 2));
    }

    static error(message, error = null) {
        console.error(`[ERROR] ${new Date().toISOString()} - ${message}`);
        if (error) console.error(error.stack || error);
    }

    static warn(message, data = null) {
        console.warn(`[WARN] ${new Date().toISOString()} - ${message}`);
        if (data) console.log(JSON.stringify(data, null, 2));
    }

    static debug(message, data = null) {
        if (process.env.DEBUG === 'true') {
            console.log(`[DEBUG] ${new Date().toISOString()} - ${message}`);
            if (data) console.log(JSON.stringify(data, null, 2));
        }
    }
}

module.exports = Logger;
