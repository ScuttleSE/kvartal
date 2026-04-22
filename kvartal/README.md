# kvartal

Flask app that fetches a Kvartal RSS feed and serves per-show filtered feeds.

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /shows` | List available shows with slugs and episode counts |
| `GET /feed/<slug>` | RSS feed filtered to a single show |
| `GET /feed/other` | RSS feed of episodes not belonging to a named show |

Shows with fewer than `MIN_SHOW_SIZE` episodes are grouped into `/feed/other`.
The upstream feed is cached for `CACHE_TTL` seconds.

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```
FEED_URL=      # URL of the upstream RSS feed
CACHE_TTL=600  # Cache lifetime in seconds
MIN_SHOW_SIZE=5  # Minimum episodes for a show to get its own feed
```

## Running locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Docker

```bash
docker run \
  -e FEED_URL=... \
  -e CACHE_TTL=600 \
  -e MIN_SHOW_SIZE=5 \
  -p 5000:5000 \
  ghcr.io/<you>/kvartal
```

The image is automatically built and pushed to GitHub Container Registry on every push to `main`.
