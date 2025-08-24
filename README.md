#  Athena – A Simple Discord Music Bot

Athena is a lightweight music bot for Discord written in Python using [discord.py](https://discordpy.readthedocs.io/) and [yt-dlp](https://github.com/yt-dlp/yt-dlp).  
It can join your voice channels, play music directly from YouTube links or search queries, and provides basic queue and playback controls.

---

##  Features
-  **Join/Leave** voice channels on command  
-  **Play music** from YouTube URLs or searches  
-  **Pause / Resume** playback  
-  **Skip** the current track  
-  **Loop** the current song  
-  **Now Playing** info with title, duration, thumbnail, and requester  
-  **Search + Pick**: search YouTube with `&search <query>` and pick results with `&pick <1-5>`  

##  Installation

### Requirements
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) (must be installed and available in your system PATH)
- Dependencies:  
```bash
 pip install discord.py yt-dlp pynacl
```
  

---

Clone the repo 

```bash
git clone https://github.com/YOURUSERNAME/Athena.git
cd Athena
```


Set up your bot token

Go to the Discord Developer Portal
.

Create an application → Add a bot.

Copy the Bot Token and store it securely in an environment variable:

export DISCORD_BOT_TOKEN="your_token_here"


(On Windows PowerShell: setx DISCORD_BOT_TOKEN "your_token_here")

 Never commit your bot token to GitHub.
Use .env files or environment variables to keep secrets safe.

---

## Usage

Run Athena by simply typing

```bash
 python Athena.py
```

As mentioned above, you will need to register your application in the Discord developer dashboard, I'll be happy to provide more instructions if more are necessary!

Once registered, you simply need to add Athena to your personal server using the appropriate OAuth2 URL, and after that, you're golden!


---

## Commands

- `&join` – Have the bot join your current voice channel  
- `&leave` – Disconnect the bot from the channel  
- `&play <url>` – Play a YouTube song (auto-joins if not in VC)  
- `&pause` – Pause playback  
- `&resume` – Resume playback  
- `&skip` – Skip the current song  
- `&loop` – Toggle looping the current track  
- `&nowplaying` – Show details of the current song  
- `&search <query>` – Search YouTube for a song (lists 5 results)  
- `&pick <1-5>` – Play one of the search results  
- `&help` – Display all commands  


---

## Roadmap

The next features I plan to implement are:

-  **Queue**  Queue up songs and skip/return between them. 
-  **Seek** Skip to a precise point in the song (1:30 for example)  
-  **Volume Control** Change Volume up/down  
-  **Reaction Based Controls** Click buttons on nowplaying instead of typing to use its features!  
- **Spotify Support** Use Spotify URLs as well as Youtube ones. 


---

## Contributing.

Pull requests are more than welcome! Please feel free to fork and extend Athena's features for your own use!




