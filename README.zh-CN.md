# 作者贡献生成器

基于 Python / Tkinter 的本地桌面应用，用于整理 CRediT 作者贡献。

## 安装与运行

需要 Python 3.10+，并包含 Tkinter。

    python -m pip install -r requirements.txt
    python author_contributions.py

Windows 安装依赖后也可双击 run_server.bat。

## 使用

添加中文或英文姓名；只填中文会转为拼音，例如张绪霞 → Zhang Xuxia。
勾选贡献、选择模板、生成声明，再复制或导出 TXT。修改信息后需要重新生成。
默认英文，可切换中文并记住选择。支持 JSON 保存、加载与自定义模板。

自动拼音、复姓、多音字和缩写需要核对。期刊模板不是官方投稿要求。
不要上传个人作者配置、虚拟环境或本机设置。examples 中仅使用演示姓名。
发布步骤见 RELEASE_CHECKLIST.md；本项目采用 [MIT 许可证](LICENSE)，Copyright (c) 2026 MaQ。

常用名：输入姓名后点击“保存输入姓名”，或点击“收藏本次作者”批量收藏。双击名单或多选后点击“加入本次投稿”。团队名单保存于 common_names.json，重启保留；本次作者与贡献勾选重启清空。该名单已排除 Git 上传。
