const dotenv = require('dotenv');
dotenv.config();

/**
 * 환경 변수 검증 및 설정
 */
class Config {
    constructor() {
        this.validateRequiredEnvVars();
        this.github = {
            token: process.env.GITHUB_TOKEN,
            owner: process.env.GITHUB_OWNER,
            repo: process.env.GITHUB_REPO,
            projectNumber: parseInt(process.env.PROJECT_NUMBER, 10)
        };

        this.rss = {
            url: process.env.MANTIS_RSS_URL
        };

        this.defaults = {
            status: process.env.DEFAULT_STATUS || 'Todo',
            milestone: process.env.DEFAULT_MILESTONE || null
        };

        this.dryRun = process.env.DRY_RUN === 'true' || process.argv.includes('--dry-run');
    }

    validateRequiredEnvVars() {
        const required = ['GITHUB_TOKEN', 'GITHUB_OWNER', 'GITHUB_REPO', 'PROJECT_NUMBER', 'MANTIS_RSS_URL'];
        const missing = required.filter(key => !process.env[key]);

        if (missing.length > 0) {
            throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
        }
    }
}

module.exports = new Config();
