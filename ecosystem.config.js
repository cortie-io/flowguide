module.exports = {
  apps: [
    {
      name: 'naito-api',
      script: '/home/ubuntu/nodi/server/.venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000 --workers 1',
      cwd: '/home/ubuntu/nodi/server',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        PYTHONPATH: '/home/ubuntu/nodi/server'
      },
      error_file: '/home/ubuntu/nodi/logs/naito-api-error.log',
      out_file: '/home/ubuntu/nodi/logs/naito-api-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss'
    },
    {
      name: 'naito-web',
      script: '/home/ubuntu/nodi/chatbot/node_modules/.bin/next',
      args: 'dev --webpack -p 3000',
      cwd: '/home/ubuntu/nodi/chatbot',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'development',
        N9N_API: 'http://127.0.0.1:8000'
      },
      error_file: '/home/ubuntu/nodi/logs/naito-web-error.log',
      out_file: '/home/ubuntu/nodi/logs/naito-web-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss'
    }
  ]
};
