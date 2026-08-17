# Luogu Saver History

This repository records daily archive totals from `api.luogu.me` and publishes the resulting history at [GitHub Pages](https://someonehx.github.io/lgs-history/).

The scheduled GitHub Actions workflow runs daily at 08:15 China Standard Time and can also be run manually from the **Actions** tab. Every successful run reads these public endpoints:

- `GET https://api.luogu.me/article/count`
- `GET https://api.luogu.me/paste/count`

It appends or updates that day's row in [data/history.csv](data/history.csv), then regenerates the Pages report and SVG charts. The workflow only commits generated historical data and site output when something changed.

## Charts in Markdown

Use these stable Pages URLs in any Markdown document. SVG keeps charts crisp and small when embedded.

```md
![Article total](https://someonehx.github.io/lgs-history/charts/articles-total.svg)
![Paste total](https://someonehx.github.io/lgs-history/charts/pastes-total.svg)
![Daily additions](https://someonehx.github.io/lgs-history/charts/daily-additions.svg)
![Monthly additions](https://someonehx.github.io/lgs-history/charts/monthly-additions.svg)
![Archive composition](https://someonehx.github.io/lgs-history/charts/composition.svg)
```

## First publication

1. Push this repository to `https://github.com/SomeoneHX/lgs-history.git`.
2. In the repository **Settings → Pages**, set **Source** to **GitHub Actions**.
3. Run **Collect and publish statistics** once with `workflow_dispatch` to capture the first snapshot and deploy the site.

`API_BASE_URL` can be overridden when running the collector locally, for example `API_BASE_URL=https://api.luogu.me python scripts/fetch_stats.py`.
