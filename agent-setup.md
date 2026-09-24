# D Robotics Workspace Agent Setup

本文档给 agent 使用。用户把包含本文件的目录放到任意位置后，agent 按以下步骤完成项目初始化。

当前发布版本：`v1.0.0`。

## 1. 定位资源目录

找到本文件（`agent-setup.md`）所在目录的绝对路径，记为 `RESOURCE_DIR`。

## 2. 确认项目根目录

按以下顺序确认 `PROJECT_ROOT`：

1. 检查用户当前工作目录及其逐级父目录，查找是否存在 `AGENTS.md` 或 `CLAUDE.md`
2. 如果找到，将包含该文件的目录作为候选 `PROJECT_ROOT`，**必须向用户确认**是否正确
3. 如果未找到，将用户当前工作目录作为候选 `PROJECT_ROOT`，**必须向用户确认**

未经用户确认，不得继续执行后续步骤。所有资源必须安装到此确认后的 `PROJECT_ROOT` 中。

## 3. 确保 AGENTS.md 或 CLAUDE.md 存在

检查 `PROJECT_ROOT` 下是否存在 `AGENTS.md` 或 `CLAUDE.md`：

- 如果已存在，直接使用，跳到下一步
- 如果都不存在，根据当前 agent 类型创建：
  - **Claude Code** → 创建 `CLAUDE.md`
  - **其他 agent**（Codex、Cursor 等） → 创建 `AGENTS.md`
- 创建空文件即可（`setup.sh` 会向其中注入路由规则）

## 4. 执行安装

```bash
bash "$RESOURCE_DIR/setup.sh" "$PROJECT_ROOT"
```

这条命令会：

- 在 `PROJECT_ROOT` 下创建 `.drobotics-s/` 目录
- 铺设 docs、skills、DROBOTICS-S.md、skill-index.json、VERSION
- 记录 `INSTALLED_REF`（安装来源锚点；未用 `--ref` 时回退为 VERSION 值）
- 跳过含 `eval.json` 的 `test/` 目录
- 向 `CLAUDE.md` / `AGENTS.md` 注入路由规则（幂等，不会重复注入）

### 升级已安装的 workspace

```bash
bash "$RESOURCE_DIR/setup.sh" --update --ref v1.0.0 "$PROJECT_ROOT"
```

`--update` 先比较已安装 `.drobotics-s/VERSION` 与资源 VERSION：相同则直接跳过（幂等）；不同则**重建** `.drobotics-s/`（先删除再铺设，旧版残留文件会被清除，但用户在 `.drobotics-s/` 内的本地修改也会被丢弃）。`--force` 在版本相同时强制重建。`--ref` 记录进 `INSTALLED_REF` 供安装器比对 registry。

## 5. 安装后检查

```bash
test -f "$PROJECT_ROOT/.drobotics-s/DROBOTICS-S.md"
test -f "$PROJECT_ROOT/.drobotics-s/VERSION"
test -f "$PROJECT_ROOT/.drobotics-s/INSTALLED_REF"
test -f "$PROJECT_ROOT/.drobotics-s/skill-index.json"
test -f "$PROJECT_ROOT/.drobotics-s/skills/drobotics-router/SKILL.md"
```

## 6. 初始化后如何使用

1. 先看 `.drobotics-s/DROBOTICS-S.md` 了解工作区规则和内置 skill 清单
2. 查找具体 skill 路径时，以 `.drobotics-s/skill-index.json` 为准
3. 当任务属于 D Robotics 范畴但尚未明确落到某个具体 skill 时，先走 `.drobotics-s/skills/drobotics-router/SKILL.md` 做顶层路由
4. 再由 drobotics-router 顶层 skill 分流到具体的子 skill

## 7. 官方 RDK 文档 MCP

回答 OE S 工具链行为、命令、参数、API、配置或版本问题时，Agent 环境必须提供 RDK 文档 MCP：使用 `mcp__rdk_docs__search_docs`（`manual=oe-s`、`source=docs`）检索，并用 `mcp__rdk_docs__get_page` 阅读官方页面。每次任务都要检索，不能因本地 Skill 或参考文档已有相同说法而跳过。

此仓库不安装或配置 MCP。连接方式由 Agent 宿主环境负责；如果工具不可用、没有命中相关页面或证据不足，报告阻塞，不要用旧服务地址、本地文档或模型记忆替代。

## 8. 常见问题

- 如果 `setup.sh` 报找不到 `drobotics-s/` 目录，确认资源目录结构完整
- 如果 `.drobotics-s/` 已存在：直接重跑安装是覆盖式铺设（合并，不删旧文件）；升级请用 `--update`（重建式，先删后铺、无旧文件残留，但 `.drobotics-s/` 内的本地修改会丢失）
- `setup.sh` 只会向已有的 `CLAUDE.md` / `AGENTS.md` 注入路由规则；如果两个文件都不存在，必须先按第 3 步创建对应文件再执行安装
