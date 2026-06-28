@echo off
setlocal
cd /d D:\Sera\frontend
if not exist node_modules (
  npm install
)
npm run dev
