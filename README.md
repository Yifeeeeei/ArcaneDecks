# ArcaneDecks

《奥术纪元》预组卡组仓库。其他组件可以通过 GitHub Pages 读取根目录的
`index.json`，获得最新的预组卡组。

## 添加或修改卡组

1. 在 `decks/` 下选择合适的子文件夹；需要时可以继续创建子文件夹。
2. 复制一份已有的 `.json` 文件，修改文件名和内容。
3. 在仓库根目录运行：

   ```bash
   python3 publish.py
   ```

脚本会递归发现 `decks/` 下的所有 JSON，检查基本格式，重新生成
`index.json`，然后执行 Git add、commit 和 push。

每副卡组只需要三个字段：

```json
{
  "name": "卡组名称",
  "version": ["卡牌版本"],
  "deckCode": "从 ArcaneComposer 复制的卡组代码"
}
```

一副卡组使用多个版本时，将它们依次写进 `version` 数组。脚本只检查存储
格式，不检查卡号、版本内容或卡组是否合法。

只想生成索引、不提交时，可以运行：

```bash
python3 publish.py --generate-only
```

