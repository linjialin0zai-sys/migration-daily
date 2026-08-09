# 迁移日报 · 雷达管线 v0.1

把「今日雷达」从演示壳变成每天真跑的系统。当前状态：**抓取 → 评分 → 双轨选取 → 渲染 全链路已验证**（2026-08-10 用 HN 真实数据 + mock 评分端到端跑通）。

## 文件

| 文件 | 作用 |
|---|---|
| `sources.yaml` | 信源清单 + 去重规则 + 每日双轨配额（改这里就能调雷达口味） |
| `prompts.py` | **系统大脑**：四维评分 prompt、主编一句话 prompt、拦截说明 prompt |
| `radar.py` | 主管线：抓取 → 去重 → LLM 评分 → 双轨配额选取 → 渲染 |
| `render.py` | 日报 HTML 渲染（与 PWA 壳同一视觉语言） |
| `output/` | 每天生成一页 `YYYY-MM-DD.html` |

## 跑起来（约 10 分钟）

```bash
pip install feedparser pyyaml requests

# 任何 OpenAI 兼容 API 都行；默认走 Kimi 开放平台（platform.kimi.com）
export MOONSHOT_API_KEY=sk-你的key
# 可选：export LLM_MODEL=kimi-k2.5      # 报错 model_not_found 就去控制台模型列表复制准确名字
# 可选：export LLM_BASE_URL=https://api.moonshot.cn/v1   # 境外账号用 https://api.moonshot.ai/v1

python3 radar.py            # 真跑
python3 radar.py --mock     # 不烧 token，验证流程
```

## 每天自动跑（GitHub Actions · 免费 · 推荐）

不需要服务器。约 15 分钟、一次设置永久自动：

1. **申请 Kimi API key**：platform.kimi.com → 充值（最低10元）→ 创建 API Key（每天一期成本约几毛钱）。注意：这是开放平台，和你的 Kimi App 会员是独立产品，key 和余额不互通，需单独充值
2. **建 GitHub 仓库**（建议私有）：github.com → New repository
3. **把本项目全部文件上传到仓库根目录**（含 `.github/` 隐藏文件夹，网页上传时别漏）
4. **存 key**：仓库 → Settings → Secrets and variables → Actions → New repository secret → 名称 `MOONSHOT_API_KEY`，粘贴 key
5. **开托管**（二选一）：
   - 仓库公开：Settings → Pages → Source 选 `Deploy from a branch` → 分支 `main`、目录 `/docs`，得到存档网址 `https://你的用户名.github.io/仓库名/`
   - 仓库私有：GitHub Pages 免费版不支持私有仓库，改用 **Cloudflare Pages**（免费、支持私有仓库，绑定后每日自动部署，构建命令留空、输出目录填 `docs`）
6. **验证**：Actions → migration-daily → Run workflow 手动触发一次，几分钟后 output/ 与 docs/ 里出现当日日报

之后每天北京时间 07:10 自动运行并提交，无需任何维护。

### 备选：自己的电脑/NAS 跑 cron

```cron
30 7 * * * cd /path/to/radar && /usr/bin/python3 radar.py >> radar.log 2>&1
```

生成的 HTML 是独立单文件，可以直接：邮件发送 / 挂到任意静态托管 / 复制进 PWA 的存档目录。

## 关键机制（与产品文档一一对应）

- **四维评分**：资讯价值 ×3、专业相关性 ×2、写作潜力 ×1.5、认知扩展 ×1.5；资讯价值 <5 直接不进候选（宁缺毋滥）
- **双轨配额**：能力边界+评测 2 条 / 现场+采用 1-2 条 / 规则 0-1 条 / 相邻 1 条，总数 4-7
- **反例保底**：若当天入选里没有「反例与挑战」角度且候选中有资讯价值 ≥7 的反例，挤占一席也要进
- **去重**：同一公司/模型一天最多 2 条
- **硬性否决**：无原始来源、发布会通稿、融资新闻、口水讨论，直接 reject

## 已知的坑

- arXiv RSS 周末不更新（feed 自带 skipDays），周一早上内容最多
- Hugging Face 等部分源在国内网络环境会超时，管线已做 15s 超时隔离，单源挂掉不拖死整体
- 国内社区源（即刻/公众号）需要 RSSHub 中转，部署后在 `sources.yaml` 里取消注释替换即可

## 下一步（按优先级）

1. 插入真实 API key，工作日早上跑第一期真日报
2. 把 PWA 里的「校准这条」反馈回写到 `feedback.jsonl`，每周用反馈微调 `sources.yaml` 权重和评分 prompt
3. 存档页自动生成索引（扫描 `output/` 目录）
4. 部署 RSSHub，接入中文一手案例源（这是信息差最大的圈）
