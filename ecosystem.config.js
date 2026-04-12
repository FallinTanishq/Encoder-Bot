module.exports = {
  apps: [
    {
      name: "encoder-bot",
      script: "bot.py",
      interpreter: "python3",
      restart_delay: 3000,
      max_restarts: 10,
      watch: false,
    },
  ],
};
