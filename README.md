# MetaCubeX → Egern 原生规则集自动转换

通过 GitHub Actions 每天将 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat/tree/meta/geo/geosite) 的 **Mihomo geosite YAML** 转换为 Egern 原生规则集 YAML。

- **每天北京时间约 10:17 自动构建**（GitHub 的定时任务可能延迟）。
- 也可在 Actions 页手动运行 `Convert MetaCubeX to Egern`。
- 上游访问失败、遇到不支持的语法或生成失败时，不会提交不完整的规则。
- 自动去重，并保留精确域名、域名后缀、关键词、正则和通配符匹配的区别。
- 不需要 VPS，也不需要提供个人 GitHub Token。GitHub Actions 使用其自身的 `GITHUB_TOKEN` 写入规则。

## 使用

首次运行 Actions 成功后，生成的文件位于 `rules/`，例如：

- `https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/Instagram.yaml`
- `https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/Twitter.yaml`
- `https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/Google.yaml`

在 **现有** Egern 配置 `rules:` 下增加一条，例如：

```yaml
  - rule_set:
      match: https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/Instagram.yaml
      policy: Instagram
      update_interval: 86400
```

请确保 `Instagram` 策略组存在，并将本条放在兜底规则之前。如果已存在同名分流条目，请替换而不要重复添加。

## 可修改的规则分类

编辑 `groups.json`。键是生成的文件名称，值是 MetaCubeX 的 geosite 类别。例如：

```json
{
  "Twitter": "twitter",
  "Instagram": "instagram",
  "AI": "openai"
}
```

默认生成 NodeSeek、AI（仅 openai 类别）、TG（telegram）、Google、YouTube、Twitter、Instagram、WhatsApp、PayPal、Bing、Microsoft。

注意：**MetaCubeX 的 `geosite/emby.yaml` 不存在**，请继续使用你原有的 Emby 规则集。

如果需要覆盖更广泛的 AI 相关服务，可将 `AI` 对应的 `openai` 换为 `category-ai-!cn`，但覆盖范围更广，不再只是 OpenAI。

## 转换约定

| MetaCubeX 规则 | Egern 字段 |
|---|---|
| `example.com` | `domain_set`（精确域名） |
| `+.example.com` | `domain_suffix_set`（包括根域名与子域） |
| `full:example.com` | `domain_set` |
| `domain:example.com` | `domain_suffix_set` |
| `keyword:abc` | `domain_keyword_set` |
| `regexp:...` | `domain_regex_set` |
| `*.example.com` | `domain_wildcard_set` |

**提醒**：MetaCubeX 分类可能包括第三方、营销、甚至仿冒域名。自动转换保留上游内容，不承诺所有条目都是相应服务的官方域名。使用时建议先核查来源。

## 运行和维护

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/convert.py
```

GitHub Actions 运行成功后会自动提交 `rules/*.yaml` 到默认分支。新增分类只需修改 `groups.json`；历史分类从 `groups.json` 删除后，生成任务会清理对应旧的 YAML 文件。

参考：[Egern 规则集说明](https://egernapp.com/zh-CN/docs/configuration/rules/)。
