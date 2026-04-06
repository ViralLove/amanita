'use strict';
/**
 * Канонический путь к env для deploy_full / hardhat: scripts/.env (не корень репозитория).
 */
const path = require('path');
const SCRIPTS_DOTENV_PATH = path.join(__dirname, '..', '.env');
module.exports = { SCRIPTS_DOTENV_PATH };
