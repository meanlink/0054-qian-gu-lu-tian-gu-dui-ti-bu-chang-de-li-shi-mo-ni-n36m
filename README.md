# 迁鼓 · 露天鼓队替补场地历史模拟

港堤鼓队由 18 位队员和 2 名外联组成。暑期排练结束后要用历史天气与场地记录回顾替场安排。原本单看当天温度峰值，无法复核提前两格的历史信号、临时场地重叠或会费场租。系统把历史气温窗口接到替场测试单和场租复核，下游由队内财务核账。

## 一天的工作顺序

1. 08:45 查八月 12 日 H-12 的场地预留与 14 人规模。
2. 09:00 核对历史堤台半小时回放归档 CSV，H-20 缺 14:30 读数。
3. 09:20 用 3 个相似日和 P80 重跑 15:00–17:00。
4. 09:40 查看 15:30 / 16:00 两档替场窗口与 12 格回测。
5. 10:05 H-16 的替补场地不够 10 人，不能出票。
6. 10:20 为 H-12 签下街廊馆票据，预计 76 元；同场重叠的 H-14 拒绝。
7. 11:00 登记实收 7600 分并锁档。

## 算法口径

相似日用排练开始前两格温度差加上湿度差除以 10 的和排序，且候选日必须早于目标历史日。各拟排半小时取相似日最近秩分位，模拟阈值固定 35 ℃。以样本最后三个过往日逐日用当时可见候选重跑，记录 MAE 与分位覆盖率。阈值只用于复现合成情景。场租按半小时整数分计。

## 上手

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
docker compose down --remove-orphans
```

前端走本机 **18448**，API 走 **19448**，PostgreSQL 走 **17948**。本地开发可在安装 Python 3.11、PostgreSQL 和 Redis 后配置与 Compose 相同的环境变量，在 backend 运行 `uvicorn app:app --reload`，前端以 Nginx 同源代理启动。

| 角色 | 邮箱 | 业务权限 |
|---|---|---|
| 录入员 | operator@demo.local | 订正历史抄录并运行回放 |
| 复核员 | reviewer@demo.local | 审核替场票据、费用和结算 |
| 查阅员 | viewer@demo.local | 看历史预留、证据、模拟和留底 |

三个演示账号默认密码均为 `Demo2026!`。使用本地合成样本，seed 只插入缺失的自然键。关闭 `SEED_DEMO` 可跳过自动 seed。使用自己的 `JWT_SECRET`、`POSTGRES_PASSWORD` 和 `DEMO_PASSWORD` 部署。

| 目录 | 技术与职责 |
|---|---|
| backend | Python 3.11 / FastAPI，使用 PostgreSQL 16；Worker 轮询持久化队列，Redis 为登录限流及健康检查提供支持 |
| frontend | Nginx、HTML、CSS、JavaScript ES modules，HTTP 同源代理 |
| docker-compose.yml | 5 服务及健康检查、独立卷；Redis 与 worker 无宿主端口 |

角色、作业状态在 `backend/core.py`、`frontend/base.js` 定义，在 `backend/core.py`（鉴权、队列）与 `backend/worker.py` 使用。领域阶段由数据库约束与业务服务维护，`frontend/view.js` 负责显示。接口输出为最新已提交状态。

全部为八月合成记录的历史回放；时段标识及固定阈值用于档案模拟。

MIT License
