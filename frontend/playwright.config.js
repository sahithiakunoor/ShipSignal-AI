import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',use:{baseURL:process.env.E2E_BASE_URL||'http://127.0.0.1:5173',headless:true,launchOptions:{executablePath:process.env.CHROMIUM_PATH||undefined}},reporter:'list',timeout:60000});
