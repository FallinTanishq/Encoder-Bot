module.exports = {
  apps: [
    {
      name: "encoder-bot",
      script: "bot.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      env: {
        BOT_TOKEN: process.env.BOT_TOKEN,
        OWNER_ID: process.env.OWNER_ID,
        API_ID: process.env.API_ID,
        API_HASH: process.env.API_HASH,
      },
    },
  ],
};
