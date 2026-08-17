# 洛谷存档历史统计

本仓库每日记录 `api.luogu.me` 的存档总量，并在 [GitHub Pages](https://someonehx.github.io/lgs-history/) 展示历史统计图表。

GitHub Actions 会在每天北京时间 08:15 自动运行，也可以在 **Actions** 页面手动运行。每次成功运行均会读取以下公开接口：

- `GET https://api.luogu.me/article/count`
- `GET https://api.luogu.me/paste/count`

工作流会向 [data/history.csv](data/history.csv) 新增或更新当天的数据，再重新生成 Pages 页面和 SVG 图表。仅在数据或产物变化时创建提交。

公开 CSV 地址：[https://someonehx.github.io/lgs-history/data/history.csv](https://someonehx.github.io/lgs-history/data/history.csv)。

## 在 Markdown 中嵌入图表

以下是稳定的 Pages 图表地址，可直接放入任意 Markdown 文档。SVG 图表在各种尺寸下均能保持清晰。

```md
![文章总量](https://someonehx.github.io/lgs-history/charts/articles-total.svg)
![剪贴板总量](https://someonehx.github.io/lgs-history/charts/pastes-total.svg)
![每日新增](https://someonehx.github.io/lgs-history/charts/daily-additions.svg)
![每月新增](https://someonehx.github.io/lgs-history/charts/monthly-additions.svg)
![存档构成](https://someonehx.github.io/lgs-history/charts/composition.svg)
```

## 首次发布

1. 将本仓库推送至 `https://github.com/SomeoneHX/lgs-history.git`。
2. 在仓库的 **Settings → Pages** 中将 **Source** 设为 **GitHub Actions**。
3. 通过 `workflow_dispatch` 手动运行一次 **采集并发布统计数据**，以采集首条数据并部署站点。

本地运行采集器时可通过 `API_BASE_URL` 覆盖 API 地址，例如：`API_BASE_URL=https://api.luogu.me python scripts/fetch_stats.py`。
