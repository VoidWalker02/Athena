# Athena – A Simple Discord Music Bot  

Have you ever wanted to play music in your Discord VC using YouTube links, but hate the built-in Watch Together ads or can’t find what you want on Spotify?  
**Fear no more, your self-hostable solution is here!**  

**Athena** is a lightweight, open-source Discord music bot written in Python using [discord.py](https://discordpy.readthedocs.io/) and [yt-dlp](https://github.com/yt-dlp/yt-dlp).  
She can join your voice channels, play and queue music directly from YouTube, and more! 

---

##  Features  

-  **Join / Leave** voice channels on demand  
-  **Play music** from YouTube URLs or search queries  
-  **Pause / Resume** playback  
-  **Skip** the current track  
-  **Loop** the current song  
-  **Volume Control** up to 200%  
-  **Queue System** with `&queue`, `&skipto`, `&shuffle`, and `&clear`  
-  **Seek** to a specific timestamp 
-  **Search + Pick**: search YouTube with `&search <query>` and select results with `&pick <1–5>`  
-  **Playlist Support**: enqueue entire YouTube playlists  
- **Now Playing** embed with title, duration, thumbnail, and requester   

---

##  Installation  

### Requirements  

- **Python 3.10+**  
- **FFmpeg** (must be installed and available in your system PATH)  
- **Dependencies**:  
  ```bash
  pip install discord.py yt-dlp PyNaCl
  ```

---

### Clone the Repository  

```bash
git clone https://github.com/YOURUSERNAME/Athena.git
cd Athena
```

---

### Set Up Your Bot Token  

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).  
2. Create an application → Add a **bot user**.  
3. Copy the **Bot Token** and store it safely as an environment variable:  

   ```bash
   export DISCORD_BOT_TOKEN="your_token_here"
   ```
   **Windows PowerShell**:
   ```powershell
   setx DISCORD_BOT_TOKEN "your_token_here"
   ```

>  **Never commit your token** to GitHub. Use environment variables or `.env` files to keep secrets safe.

---

##  Usage  

Run Athena with:  
```bash
python Athena.py
```

Invite your bot to a server using the OAuth2 URL generated from the Developer Portal (scopes: `bot`, `applications.commands`; permissions: *Connect*, *Speak*, *Send Messages*).  
Once she’s in your server, summon her to your VC with `&join` and start playing music.

---

## 🎛️ Commands  

| Command | Description |
|----------|-------------|
| `&join` | Join your current voice channel |
| `&leave` | Disconnect from the voice channel |
| `&play <url>` | Play a YouTube video |
| `&pause` | Pause playback |
| `&resume` | Resume playback |
| `&skip` | Skip the current song |
| `&loop` | Toggle looping for the current track |
| `&nowplaying` | Display the current song info |
| `&queue` | Show queued songs |
| `&skipto <index>` | Skip directly to a position in the queue |
| `&shuffle` | Randomize queue order |
| `&clear` | Clear the queue |
| `&vol <0-200>` | Change playback volume |
| `&seek <time>` | Jump to a specific timestamp |
| `&search <query>` | Search YouTube for songs |
| `&pick <1-5>` | Play one of the search results |
| `&playlist <url>` | Add an entire YouTube playlist |
| `&move <old> <new>` | Reorder a track in the queue |

---

##  Roadmap  

Future updates planned for Athena include:  
-  **Spotify Support**  
-  **Lyrics Integration** using public APIs  
-  **Docker & Systemd Deployment** for easy hosting  

---

##  Contributing  

Pull requests are welcome!  
If you’d like to improve Athena or add new features, feel free to fork the repository and open a PR.  
Bug reports and feature requests can be submitted through the GitHub Issues tab.

---

## Credits  

- [discord.py](https://github.com/Rapptz/discord.py)  
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)  
- FFmpeg project  
- All my friends who helped me test it!  