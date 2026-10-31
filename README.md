# MetaCubeX → Egern 全分类自动转换仓库

[![GitHub Actions](https://github.com/Misakanei/meta-to-egern/actions/workflows/update-rules.yml/badge.svg)](https://github.com/Misakanei/meta-to-egern/actions/workflows/update-rules.yml)

每天通过 GitHub Actions **自动发现** MetaCubeX [meta 规则分支](https://github.com/MetaCubeX/meta-rules-dat/tree/meta)，将全部常规 GeoSite、GeoIP 与 Lite 规则转换成 **Egern 原生 YAML**。不是仅转换 `groups.json` 中的 11 个常用分类，**新分类上线时自动发现，旧分类移除时自动清理**。

## 覆盖范围

| 上游分类 | 发布目录 | 自动更新 |
|---|---|---|
| `geo/geosite/*.yaml` | `rules/geosite/*.yaml` | ✅ 全量 |
| `geo/geoip/*.yaml` | `rules/geoip/*.yaml` | ✅ 全量 |
| `geo-lite/geosite/*.yaml` | `rules/lite/geosite/*.yaml` | ✅ 全量 |
| `geo-lite/geoip/*.yaml` | `rules/lite/geoip/*.yaml` | ✅ 全量 |
| `asn/AS*.list` | `rules/asn/AS*.yaml` | ⚠️ 按需发布，不默认全量生成 |

**ASN 说明：** MetaCubeX 的 ASN 规则是数万组单独的 IP 网段文件，GitHub 一次性提交数万个小文件会给仓库和日常自动构建造成不必要的负担。我们将全部 ASN 类别索引到 `catalog/asn.json`，如需具体 ASN 的网段原样转换，可通过 Actions 的 `asn` 输入手动生成，不限制于预设分组。其转换结果基于原始 IP 列表而不是用 Egern 的 `asn_set` 猜测对应关系。

忽略 `.mrs`、`.list`、`classical/` 的重复格式文件，仅将它们对应的 YAML 数据转为 Egern 原生格式。ASN 按需处理 `.list`。

## 直接订阅 Egern

以 Instagram 为例：

```yaml
rules:
  - rule_set:
      match: https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/geosite/instagram.yaml
      policy: Instagram
      update_interval: 86400
```

GeoIP 规则：

```yaml
rules:
  - rule_set:
      match: https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/geoip/telegram.yaml
      policy: Telegram
      update_interval: 86400
```

精简版地址示例：

```text
https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/lite/geosite/google.yaml
https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/lite/geoip/cn.yaml
```

原先发给用户的**11 个兼容地址**仍保留，例如：

```text
https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/Instagram.yaml
https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/Twitter.yaml
```

兼容别名列表在 `groups.json`，只用于维持老地址，不再限制全量转换范围。

**索引**：[catalog/index.json](catalog/index.json)（分类和规则数）、[catalog/asn.json](catalog/asn.json)（所有 ASN 分类名）。

## 自动更新原理

1. 北京时间约 **每天 10:17** 定时更新，也支持 GitHub Actions 的 `workflow_dispatch`。
2. 通过 sparse checkout 只拉取 MetaCubeX 的四个 YAML 规则目录，避免下载海量 ASN 文件。
3. 离线扫描每个 `*.yaml`，转换并严格验证数据；**全部校验通过后才发布**，防止上游异常覆盖好规则。
4. 自动生成 YAML、索引和兼容别名，GitHub Actions 自动提交改变的文件。
5. 改动 `scripts/`、`tests/`、`groups.json` 时也立即触发全量更新。

### ASN 按需发布

在 [Actions](https://github.com/Misakanei/meta-to-egern/actions/workflows/update-rules.yml) 点击 **Run workflow**，在 `asn` 输入：

```text
AS13335,AS15169
```

完成后即可订阅：

```text
https://raw.githubusercontent.com/Misakanei/meta-to-egern/main/rules/asn/AS13335.yaml
```

每次最多输入 20 个 ASN。未来每次重新运行可补充其他 ASN；不会删除已经发布的 ASN 规则。自动更新当前只针对全量四个 YAML 类别；已发布的 ASN 规则需要手动重新运行以获取最新 IP 网段。

## 开发

本地准备 MetaCubeX `meta` 分支（目录为 `upstream/`）：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/convert.py --upstream upstream
```

单独更新 ASN：

```bash
python scripts/convert_asn.py --asn AS13335,AS15169
```

依据 [Egern 官方规则集格式说明](https://egernapp.com/zh-CN/docs/configuration/rules/) 转换为 `domain_set` / `domain_suffix_set` / `domain_keyword_set` / `domain_regex_set` / `ip_cidr_set` / `ip_cidr6_set` 等字段。

本仓库只负责规则格式转换，不保证上游规则的正确性或数据隐私属性，实际分流效果仍取决于 Egern 客户端及策略匹配顺序。
