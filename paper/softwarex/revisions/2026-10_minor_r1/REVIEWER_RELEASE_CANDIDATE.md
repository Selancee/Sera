# R1 本地发布候选验收

日期：2026-10-03。候选源提交：`b9589ee7a0aee4a8bfeccf11bab65f53c04bcc9f`，打包时 Git 工作区干净。此为本地候选，未 push、公开发布、更新 DOI 或提交期刊。

## 交付物

- [源代码 ZIP](../../../../artifacts/softwarex_revision_20261003_review/candidate_b9589ee/seraedit-revision-b9589ee-r1-source.zip)：4,345 个清单文件；SHA-256 `4b94ca1cb1fffb1034b3c622514ff36a67860469cf6447667f3380aca9f81d93`。
- [R1 稿件与证据 ZIP](../../../../artifacts/softwarex_revision_20261003_review/candidate_b9589ee/seraedit-revision-b9589ee-r1-softwarex-manuscript.zip)：81 个清单文件；SHA-256 `21c7e49a933f0f60e8da8df149dc97147abb8180705fa143722d0ae817cb2182`。
- [正文 DOCX](manuscript/seraedit_softwarex.docx)、[逐点回复 DOCX](RESPONSE_TO_REVIEWERS.docx)、[Cover letter DOCX](submission/COVER_LETTER.docx)。

## 独立验收

源 ZIP 全部清单字节已核对，并在新临时目录解压执行：447 项 Python 测试通过，0 失败、0 错误、0 跳过；fixture 复现检查通过；审稿演示 6/6 通过；真实 DeepSeek 保存结果的离线完整性与指标复算通过。使用现有 Python 3.12.5 依赖环境，不宣称重新安装全部依赖。证据见 REVIEWER_SOURCE_ARCHIVE_VALIDATION.json 和 REVIEWER_SOURCE_ARCHIVE_TESTS.xml。

稿件 ZIP 每个文件与打包时工作区逐字节一致，包含 R1 正文、回复、Cover letter、桥接截图与原始证据，不包含旧 manuscript/submission 目录。证据见 REVIEWER_MANUSCRIPT_ARCHIVE_VALIDATION.json。新增打包回归在本轮相关 33 项测试中通过，见 REVIEWER_FOCUSED_TESTS.xml。

这些 ZIP 固定于上述提交；本回执及本次归档验收文件在打包后生成，因此不在所验收 ZIP 内。ZIP 中历史的“最终归档待核验”描述由本回执补充关闭，未重写原始候选文件。旧 ff82c74 的 445 测试和旧 DOI 仍仅指向其原有版本，不作为本候选已公开的证明。

## 尚待投稿前完成

新版公开代码/数据归档及不可变链接、托管 CI；作者对逐文件 SPDX sidecar 替代行内标头的回应进行审阅；修改标记稿、Editorial Manager 原上传材料和组装 PDF 核对。不得将本地测试通过等同于期刊录用或最终投稿完成。
