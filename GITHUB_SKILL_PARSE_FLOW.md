# GitHub Skill 解析流程说明

本文档描述当前 `v2.1` 代码里 GitHub Skill 的实际解析流程，基于：

- [app/modules/github_skills/service.py](/Users/shoes/skillnetic/v3/backend/app/modules/github_skills/service.py)
- [app/modules/github_skills/schemas.py](/Users/shoes/skillnetic/v3/backend/app/modules/github_skills/schemas.py)

不是产品理想态说明，而是当前后端真实实现。

## 1. 入口

当前解析入口：

- `POST /api/admin/v1/github-skills/parse`

请求体：

```json
{
  "github_url": "https://github.com/muxuuu/serenity-skill.git"
}
```

路由会调用：

- `GithubSkillService.parse_repo(github_url)`

它内部实际执行：

- `GithubSkillService._build_parse_result(github_url)`

## 2. URL 解析规则

使用正则 `GITHUB_HOST_RE` 解析 GitHub 仓库地址。

当前支持：

- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `git@github.com:owner/repo.git`
- `github.com/owner/repo`

当前行为：

1. 去掉首尾空格
2. 如果是 `github.com/...`，自动补成 `https://github.com/...`
3. 校验 host 必须是 `github.com`
4. 提取 `owner` 和 `repo`
5. 自动去掉 `.git`
6. 生成标准化结果

输出结构：

```json
{
  "owner": "muxuuu",
  "repo": "serenity-skill",
  "repo_full_name": "muxuuu/serenity-skill",
  "normalized_url": "https://github.com/muxuuu/serenity-skill",
  "clone_url": "https://github.com/muxuuu/serenity-skill.git"
}
```

非法 URL 会直接抛：

- `400 invalid github url`

## 3. GitHub API 请求过程

解析阶段会请求 4 类 GitHub 数据：

1. 仓库元信息
   - `GET https://api.github.com/repos/{owner}/{repo}`
2. `SKILL.md`
   - `GET https://api.github.com/repos/{owner}/{repo}/contents/SKILL.md`
3. `README.md`
   - `GET https://api.github.com/repos/{owner}/{repo}/contents/README.md`
4. `LICENSE`
   - `GET https://api.github.com/repos/{owner}/{repo}/contents/LICENSE`

请求头：

- `Accept: application/vnd.github+json`
- `User-Agent: Skillnetic-GitHub-Importer`
- 如果配置了 `settings.github_api_token`
  - 自动带 `Authorization: Bearer <token>`

## 4. GitHub 异常处理

当前异常处理逻辑：

- 仓库不存在或无法访问：
  - `404 GitHub 仓库不存在或不可访问`
- 命中 GitHub rate limit：
  - `429 GITHUB_RATE_LIMITED`
- GitHub API 其他 HTTP 错误：
  - `502 github api failed: {status}`
- 当前机器连不上 GitHub：
  - `502 GitHub API 当前不可达，请检查网络或稍后重试`

注意：

- `SKILL.md` / `README.md` / `LICENSE` 这些 contents 请求如果是 404，不会中断解析
- 当前实现会把这些文件缺失当作可接受情况

## 5. 文件内容解析

### 5.1 Base64 解码

GitHub contents API 返回的 `content` 会先做 Base64 解码。

解码后保留：

- 文件文本内容
- `path`
- `sha`

### 5.2 Frontmatter 解析

如果 `SKILL.md` 以：

```md
---
...
---
```

开头，会进入 frontmatter 解析。

当前 frontmatter 解析器是手写轻量版，不是完整 YAML 解析器。

当前支持能力：

- 简单 `key: value`
- 基于缩进的简单对象嵌套
- 跳过空行和 `#` 注释行

当前限制：

- 不支持复杂 YAML 语法
- 不支持数组语法
- 不支持多行字符串
- 不支持更复杂的类型推断

所以这里是 MVP 级解析，不是严格 YAML parser。

### 5.3 README 摘要提取

如果有 `README.md`，会提取“第一个非标题段落”作为候选摘要来源。

规则：

1. 按空行切段
2. 跳过以 `#` 开头的标题段
3. 取第一个普通文本段
4. 如果没找到，就回退成全文 `strip()`

## 6. 标题、摘要、描述生成逻辑

### 6.1 title

优先级：

1. `frontmatter.name`
2. `repo_json.name`
3. `repo 名`

### 6.2 description

优先级：

1. `frontmatter.description`
2. `repo.description`
3. `README` 第一段
4. `repo 名`

### 6.3 summary

优先级：

1. `frontmatter.metadata.short-description`
2. `frontmatter.metadata.short_description`
3. 截断后的 `frontmatter.description`
4. 截断后的 `README` 第一段
5. 截断后的 `repo.description`
6. `repo 名`

截断逻辑：

- 如果内容包含中文，最多 120 字符
- 否则最多 180 字符
- 会先把连续空白压成单空格

## 7. 分类、类型、难度、标签推荐逻辑

解析时会把以下文本拼起来做关键词判断：

- `title`
- `description`
- `repo.description`
- `README` 第一段
- `SKILL.md` 正文

然后走 `_recommend_meta()`。

### 7.1 当前关键词推荐规则

如果文本包含这些词之一：

- `investment`
- `market`
- `stock`
- `supply-chain`
- `value-chain`
- `research`

则推荐：

- `category = data-business-analysis`
- `skill_type = agent`
- `difficulty = advanced`
- `tags = ["投资研究", "供应链", "产业链", "股票研究", "市场扫描"]`

如果文本包含：

- `code`
- `review`
- `testing`
- `architecture`
- `frontend`
- `backend`

则推荐：

- `category = engineering`
- `skill_type = workflow`
- `difficulty = intermediate`
- `tags = ["代码审查", "测试", "架构", "开发工具"]`

如果文本包含：

- `image`
- `design`
- `visual`
- `poster`
- `canvas`

则推荐：

- `category = design-visual`
- `skill_type = prompt`
- `difficulty = intermediate`
- `tags = ["视觉设计", "图片生成", "创意设计"]`

如果文本包含：

- `writing`
- `copy`
- `content`
- `blog`
- `article`

则推荐：

- `category = writing-content`
- `skill_type = prompt`
- `difficulty = beginner`
- `tags = ["写作", "内容创作", "文案"]`

否则全部返回 `None / []`。

## 8. License 解析逻辑

当前优先级：

1. `repo_json.license.spdx_id`
2. `repo_json.license.name`
3. `frontmatter.license`

最终写入解析结果的字段是：

- `license`

## 9. parse 接口输出

当前 `parse` 接口返回结构：

```json
{
  "repo_full_name": "muxuuu/serenity-skill",
  "github_url": "https://github.com/muxuuu/serenity-skill",
  "clone_url": "https://github.com/muxuuu/serenity-skill.git",
  "default_branch": "main",
  "repo_description": "...",
  "stars_count": 0,
  "forks_count": 0,
  "watchers_count": 0,
  "open_issues_count": 0,
  "license": "MIT",
  "skill_md_found": true,
  "readme_found": true,
  "parsed": {
    "title": "...",
    "summary": "...",
    "description": "...",
    "category": "engineering",
    "skill_type": "workflow",
    "difficulty": "intermediate",
    "tags": ["代码审查", "测试", "架构", "开发工具"]
  },
  "warnings": []
}
```

## 10. parse 之后如何进入导入草稿

`parse` 只负责“解析并返回预览结果”，不写库。

真正写入导入草稿走：

- `POST /api/admin/v1/github-skills/imports`

它会再次执行解析流程，然后把以下内容写入 `github_skill_imports`：

- `repo_full_name`
- `github_url`
- `parsed_title`
- `parsed_summary`
- `parsed_description`
- `parsed_category`
- `parsed_skill_type`
- `parsed_difficulty`
- `parsed_tags`
- `parsed_license`
- `parsed_original_author`
- `raw_repo_json`
- `raw_skill_md_frontmatter`
- `raw_skill_md_preview`
- `raw_readme_preview`

当前 `import_status` 初始写成：

- `pending_review`

## 11. 审核通过后如何落正式 Skill

审核接口：

- `POST /api/admin/v1/github-skills/imports/{id}/approve`

审核通过时会：

1. 创建正式 `Skill`
2. 设置来源字段
   - `source_type = github`
   - `source_url = github_url`
   - `source_name = repo_full_name`
   - `original_author`
   - `license`
3. 创建或更新 `skill_github_sources`
4. 写入：
   - 仓库元信息
   - star/fork/watch/open issue
   - `skill_md_path/sha`
   - `readme_path/sha`
   - `license_path/sha`
   - `github_created_at/updated_at/pushed_at`
   - `last_synced_at`

注意：

- 当前 `Skill.content = None`
- 当前不会全文搬运 GitHub 仓库内容

## 12. 手动同步逻辑

接口：

- `POST /api/admin/v1/github-skills/{skill_id}/sync`

当前同步只会刷新这些数据：

- `stars_count`
- `forks_count`
- `watchers_count`
- `open_issues_count`
- `github_updated_at`
- `github_pushed_at`
- `last_synced_at`
- `skill.last_source_synced_at`

不会重新抓 `SKILL.md` 和 `README.md`。

## 13. 当前实现限制

### 13.1 网络限制

当前本地环境如果连不上 GitHub，会直接卡在 `_github_json()`，返回：

```json
{
  "detail": "GitHub API 当前不可达，请检查网络或稍后重试"
}
```

### 13.2 YAML 解析能力有限

当前 `SKILL.md` frontmatter 解析不是标准 YAML parser。

### 13.3 只查固定文件名

当前只查：

- `SKILL.md`
- `README.md`
- `LICENSE`

不会自动查：

- `README.MD`
- `readme.md`
- 子目录下的 skill 文件
- 其他许可证文件名

### 13.4 推荐规则很轻

当前分类/类型/难度/标签推荐只是关键词匹配，不是语义分类。

### 13.5 commit 信息未完整实现

当前 `skill_github_sources.last_commit_sha` 实际写的是：

- `repo_json.get("pushed_at")`

这不是严格意义上的 commit SHA，只是占位。

## 14. 当前本地联调状态

当前本地后端已经具备：

- `parse`
- `create import`
- `approve`
- `reject`
- `sync`
- `batch import`
- `batch detail`

当前 `parse` 不再是 404。

如果本地请求失败，现阶段主要原因通常是：

- GitHub API 外网不可达
- 不是后端路由不存在

