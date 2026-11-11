# 依赖边界检查

把 ARCH 里的依赖允许表译成工具规则，而不是另写一套。

## 要表达的不变量

- core / domain 不得 import UI、框架入口、具体数据库驱动、具体 HTTP 客户端。
- UI 不得 import core 内部实现，只能经公开 seam。
- 适配器可以实现端口，不得反向被 core 引用。
- 横切能力（鉴权、遥测、特性开关）只经明确的单一入口进入（Harness 文中的 Providers 思路）。

## 做法

1. 先在 ARCH 画允许表，再写工具配置。两者冲突时改配置，不改口头习惯。
2. JS/TS 可用 dependency-cruiser 或 eslint-plugin-import 的 `no-restricted-paths`；Python 可用 import-linter；其他语言用同等的包可见性或 ArchUnit 类工具。
3. 规则用包路径或目录路径表达，避免对每一个文件写特例。
4. 失败信息写成：「F-xx：`ui/` 引用了 `core/internal`，应改为经 `features/<slice>` 的公开入口。见 ARCHITECTURE §分层。」
5. 用一个故意违规文件证明规则生效，然后删掉或留在不会合并的样例分支。
