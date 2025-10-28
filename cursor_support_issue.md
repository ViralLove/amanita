Subject: Terminal Tool Repeatedly Hangs in Long Sessions

Hello Cursor Support Team,

I'm experiencing a recurring issue where the run_terminal_cmd tool becomes completely unresponsive after executing several commands in a single conversation session. The terminal enters an infinite wait state showing artifacts like "cmdand cmdand dquote>" and requires conversation restart with context loss. This has happened multiple times today. Simple commands like "node --check" or "grep" with pipes trigger the hang after the terminal has been working fine initially.

This is impacting my paid development work as I have to constantly restart conversations and recreate context instead of completing tasks efficiently. The issue occurs well before any token limits (around 200,000 out of 1,000,000), so it's not resource-related.

Could you please investigate the session on October 8, 2025 at approximately 18:30 EET (Tallinn timezone, UTC+3)? System: macOS darwin 23.1.0, zsh shell, Claude Sonnet 4.5 model. Session search code: 88888888 (I've added this code to the conversation for easier log matching). Any guidance on prevention or a fix would be appreciated.

Thank you
