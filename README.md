# StreamFlix — Flask Streaming Platform (Netflix-style)

A complete, working Netflix-style video streaming web app built with Python Flask.
Original branding is used (not Netflix's actual name/logo/content) to keep this
clean of trademark/copyright issues, but the UX matches a modern streaming
platform: landing page, auth, hero banner, browsable rows, search, my list,
and a full custom video player.

## Features

- **Landing page** for logged-out visitors (like netflix.com) with a signup CTA
- **Auth**: register / login / logout (hashed passwords via Werkzeug, sessions via Flask-Login)
- **Browse/Home**: hero banner for a featured title + horizontally scrollable
  category rows ("Trending Now", "Action & Adventure", "Documentaries", …)
- **Continue Watching row** that shows in-progress titles with a progress bar
- **Title detail page**: synopsis, metadata, "More Like This" recommendations
- **Custom video player** (`/watch/<id>`) with:
  - Play/pause, ±10s skip, seek bar, volume/mute, fullscreen
  - Keyboard shortcuts: `Space`/`k` play-pause, `←`/`→` seek, `↑`/`↓` volume, `f` fullscreen, `m` mute
  - **Resume playback** from where you left off
  - **Progress auto-sync** to the server every 8s and on pause/close
  - **"Up Next" autoplay countdown** in the final 15 seconds (Netflix-style)
  - Auto-hiding controls on inactivity
- **Search** across titles
- **My List**: add/remove titles, dedicated page
- Fully responsive dark UI

## Project structure

```
streamflix/
├── app.py                 # Routes + app factory + CLI seed command
├── config.py               # Config
├── models.py                # SQLAlchemy models
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── login.html / register.html
│   ├── browse.html
│   ├── detail.html
│   ├── watch.html
│   ├── search.html
│   └── my_list.html
└── static/
    ├── css/style.css
    └── js/main.js, player.js
```

## Setup

```bash
cd streamflix
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create tables + load sample catalog (open-license Blender Foundation films)
export FLASK_APP=app.py       # Windows (PowerShell): $env:FLASK_APP="app.py"
flask seed

# Run
python app.py
```

Then open **http://localhost:5000** — you'll land on the marketing page.
Click **Sign In → Sign up now** to create an account, then you'll be dropped
into the browse page with a working catalog you can click into and play.

## Notes on content

The seed data uses freely licensed sample videos from the Blender Foundation's
open movie projects (Big Buck Bunny, Sintel, Tears of Steel, Elephants Dream,
etc.) hosted on Google's public sample bucket, so playback works immediately
with zero configuration. To use your own catalog, edit the `seed()` function
in `app.py`, or point `Video.video_url` at your own hosted `.mp4` files.

## Extending it

- Swap SQLite for Postgres by changing `DATABASE_URL`
- Add an admin panel (Flask-Admin) for managing the catalog via a UI instead of the CLI
- Add HLS/adaptive streaming (e.g. via `hls.js`) for real transcoded content
- Add profiles per account (multiple `Profile` rows per `User`)
- Add episodic content: a `Show` → `Season` → `Episode` model, with the
  "Up Next" logic in `player.js` wired to actually queue the next episode
  instead of returning to `/browse`
