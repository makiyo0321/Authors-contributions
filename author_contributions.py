import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
import json
import os
import re
from string import Formatter

# CRediT标准的14个角色
CREDIT_ROLES = [
    ("Conceptualization", "概念化和设计研究"),
    ("Data curation", "数据管理和整理"),
    ("Formal analysis", "正式分析和统计"),
    ("Funding acquisition", "资金获取"),
    ("Investigation", "研究和实验执行"),
    ("Methodology", "方法论设计"),
    ("Project administration", "项目管理"),
    ("Resources", "资源提供"),
    ("Software", "软件开发"),
    ("Supervision", "监督和指导"),
    ("Validation", "验证和复查"),
    ("Visualization", "可视化和图表"),
    ("Writing – original draft", "撰写初稿"),
    ("Writing – review & editing", "审阅和编辑")
]

# 不同期刊的格式模板
JOURNAL_FORMATS = {
    "Elsevier": "{authors}: {role}.",
    "Springer": "{authors}: {role}.",
    "Wiley": "{authors} contributed to {role}.",
    "Nature": "{authors} {role}.",
    "Science": "{authors}: {role}.",
    "npj Digital Medicine": {"type": "author", "template": "{authors}: {role}."},
    "Custom": "{authors}: {role}."
}


class AuthorContributionsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("作者贡献生成器 - CRediT标准")
        self.root.geometry("1300x750")
        
        self.authors = {}  # {简称: {'full': 全称, 'abbr': 缩写}}
        self.author_order = []  # 作者顺序列表
        self.role_vars = {}  # {角色: {作者: BooleanVar}}
        self.display_mode = tk.StringVar(value="english")  # 显示模式
        self.format_combo = None  # 格式下拉框
        
        # 加载自定义格式
        self.load_custom_formats()
        
        self.settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        try:
            with open(self.settings_path, encoding="utf-8") as stream:
                language = json.load(stream).get("language", "English")
        except (OSError, ValueError, AttributeError):
            language = "English"
        self.language = tk.StringVar(value=language if language in ("English", "中文") else "English")
        self.common_names_path = os.path.join(os.path.dirname(__file__), "common_names.json")
        self.common_names = {}
        self.load_common_names()
        self.setup_theme()
        self.setup_ui()
        self.apply_language()
        
    def load_common_names(self):
        try:
            with open(self.common_names_path, encoding="utf-8") as stream:
                data = json.load(stream)
            if not isinstance(data, dict) or any(
                not isinstance(key, str) or not key.strip()
                or not isinstance(value, dict) or not isinstance(value.get("full"), str)
                or not value["full"].strip() for key, value in data.items()
            ):
                raise ValueError("Invalid team favorites file")
            self.common_names = data
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            messagebox.showerror("Team favorites / 常用名", str(exc))

    def commit_common_names(self, data):
        temporary = self.common_names_path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, self.common_names_path)
        except OSError as exc:
            messagebox.showerror("Team favorites / 常用名", str(exc))
            return False
        self.common_names = data
        self.refresh_common_names()
        return True

    def refresh_common_names(self):
        self.common_listbox.delete(0, tk.END)
        for key, value in self.common_names.items():
            self.common_listbox.insert(tk.END, f"{key} | {value['full']}")

    def save_entered_common(self):
        key = self.abbr_entry.get().strip()
        full = self.resolve_name(key, self.full_entry.get().strip())
        key = key or full
        if not full:
            return
        data = dict(self.common_names)
        if key in data and data[key]["full"] != full:
            if not messagebox.askyesno("Team favorites / 常用名",
                    "Replace this saved name? / 替换已保存的姓名？"):
                return
        data[key] = {"full": full, "abbr": self.generate_pinyin_abbreviation(key, full)}
        if self.commit_common_names(data):
            self.abbr_entry.delete(0, tk.END)
            self.full_entry.delete(0, tk.END)

    def save_current_as_common(self):
        data = dict(self.common_names)
        conflicts = [key for key in self.author_order if key in data
                     and data[key]["full"] != self.authors[key]["full"]]
        if conflicts and not messagebox.askyesno("Team favorites / 常用名",
                "Replace saved names with matching IDs? / 替换相同标识的已存姓名？"):
            return
        for key in self.author_order:
            data[key] = dict(self.authors[key])
        self.commit_common_names(data)

    def add_common_names(self):
        keys = list(self.common_names)
        for index in self.common_listbox.curselection():
            key = keys[index]
            if key not in self.authors:
                self.authors[key] = dict(self.common_names[key])
                self.author_order.append(key)
        self.update_author_list()
        self.update_table()

    def remove_common_names(self):
        selection = self.common_listbox.curselection()
        if not selection:
            return
        if not messagebox.askyesno("Team favorites / 常用名",
                "Remove selected favorites? Current authors are kept. / 移除所选常用名？本次作者不受影响。"):
            return
        keys = list(self.common_names)
        data = dict(self.common_names)
        for index in selection:
            del data[keys[index]]
        self.commit_common_names(data)

    def resolve_name(self, name, english):
        if english.strip():
            return english.strip()
        if not name.strip():
            return ""
        if not any("\u4e00" <= c <= "\u9fff" for c in name):
            return name.strip()
        try:
            from pypinyin import lazy_pinyin
        except ImportError:
            messagebox.showerror("Pinyin", "Please install: python -m pip install -r requirements.txt")
            return ""
        name = name.strip()
        syllables = lazy_pinyin(name)
        # Join the given name, preserving the family-name boundary.
        compound_surnames = {
            "欧阳", "司马", "上官", "诸葛", "夏侯", "东方", "皇甫", "尉迟",
            "公孙", "慕容", "司徒", "司空", "令狐", "宇文", "长孙", "端木",
            "南宫", "独孤", "闻人", "赫连", "澹台", "宗政", "濮阳", "公羊",
        }
        if all("\u4e00" <= ch <= "\u9fff" for ch in name):
            boundary = 2 if name[:2] in compound_surnames else 1
            surname = "".join(syllables[:boundary]).capitalize()
            given_name = "".join(syllables[boundary:]).capitalize()
            return " ".join(part for part in (surname, given_name) if part)
        return " ".join(part.capitalize() for part in syllables)

    def apply_language(self, event=None):
        english = self.language.get() == "English"
        translations = {
            "常用名": "Team favorites",
            "保存输入姓名": "Save entered name",
            "收藏本次作者": "Save current authors",
            "加入本次投稿": "Add to this project",
            "移除常用名": "Remove favorite",
            "双击姓名加入本次投稿；名单自动保存": "Double-click to add; favorites are saved",

            "作者管理": "Authors", "中文名 / 标识（可选）:": "Chinese name / ID (optional):",
            "英文姓名（可选，中文自动转拼音）:": "English name (optional; auto-pinyin):",
            "添加作者": "Add author", "批量导入": "Bulk import", "调整顺序:": "Order:",
            "↑ 上移": "↑ Up", "↓ 下移": "↓ Down", "编辑选中": "Edit",
            "删除选中": "Delete", "清空全部": "Clear all", "角色分配": "Contributions",
            "快速清空:": "Clear:", "清空全部勾选": "Clear assignments",
            "输出设置": "Output settings", "期刊格式:": "Template:",
            "生成贡献声明": "Generate", "添加新格式": "New template",
            "删除格式": "Delete template", "导出 TXT": "Export TXT",
            "保存配置": "Save project", "加载配置": "Load project",
            "输出结果": "Statement", "复制到剪贴板": "Copy",
            "添加作者 → 分配角色 → 生成声明 · 期刊模板仅供参考":
                "Add authors → Assign roles → Generate · Templates are examples only",
        }
        def translate(widget):
            if "text" in widget.keys():
                current = str(widget.cget("text"))
                original = getattr(widget, "_original_label", current)
                widget._original_label = original
                widget.configure(text=translations.get(original, original) if english else original)
            for child in widget.winfo_children():
                translate(child)
        translate(self.root)
        self.root.title("Authors' Contributions — CRediT" if english else "作者贡献生成器 — CRediT")
        self.display_mode.set("english" if english else "chinese")
        self.update_table()
        if event is not None:
            try:
                with open(self.settings_path, "w", encoding="utf-8") as stream:
                    json.dump({"language": self.language.get()}, stream, ensure_ascii=False)
            except OSError as exc:
                messagebox.showerror("Settings", str(exc))

    def setup_theme(self):
        self.root.minsize(1100, 680)
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        self.root.option_add("*Text.background", "#ffffff")
        self.root.option_add("*Canvas.background", "#f1f5f9")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background="#f1f5f9", foreground="#24324b")
        style.configure("TButton", padding=(10, 7), background="#e2e8f0")
        style.map("TButton", background=[("active", "#c7d2fe")])
        style.configure("TLabelframe.Label", foreground="#4338ca", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("TEntry", padding=6, fieldbackground="white")
        style.configure("Custom.Treeview", background="white", fieldbackground="white")

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Authors’ Contributions", font=("Segoe UI", 23, "bold"), foreground="#312e81").pack(anchor="w", pady=(0, 4))
        ttk.Label(main_frame, text="添加作者 → 分配角色 → 生成声明 · 期刊模板仅供参考").pack(anchor="w", pady=(0, 16))
        
        language_bar = ttk.Frame(main_frame)
        language_bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(language_bar, text="Language / 界面语言:").pack(side=tk.LEFT)
        language_choice = ttk.Combobox(language_bar, textvariable=self.language, values=("English", "中文"), state="readonly", width=12)
        language_choice.pack(side=tk.LEFT, padx=8)
        language_choice.bind("<<ComboboxSelected>>", self.apply_language)
        # 使用PanedWindow实现可调整分界
        self.paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        favorites_frame = ttk.LabelFrame(self.paned, text="常用名", padding=10)
        self.paned.add(favorites_frame, weight=1)
        ttk.Label(favorites_frame, text="双击姓名加入本次投稿；名单自动保存", wraplength=210).pack(fill=tk.X)
        favorites_list_frame = ttk.Frame(favorites_frame)
        favorites_list_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.common_listbox = tk.Listbox(favorites_list_frame, width=24, exportselection=False,
                                        selectmode=tk.EXTENDED, font=("Microsoft YaHei UI", 11))
        common_scroll = ttk.Scrollbar(favorites_list_frame, command=self.common_listbox.yview)
        common_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.common_listbox.configure(yscrollcommand=common_scroll.set)
        self.common_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.common_listbox.bind("<Double-Button-1>", lambda event: self.add_common_names())
        ttk.Button(favorites_frame, text="加入本次投稿", command=self.add_common_names).pack(fill=tk.X, pady=3)
        ttk.Button(favorites_frame, text="收藏本次作者", command=self.save_current_as_common).pack(fill=tk.X, pady=3)
        ttk.Button(favorites_frame, text="移除常用名", command=self.remove_common_names).pack(fill=tk.X, pady=3)
        self.refresh_common_names()

        # 左侧：作者管理
        left_frame = ttk.LabelFrame(self.paned, text="作者管理", padding="10")
        self.paned.add(left_frame, weight=1)
        
        # 作者输入（纵向排列）
        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(input_frame, text="中文名 / 标识（可选）:").pack(anchor='w', padx=5, pady=2)
        self.abbr_entry = ttk.Entry(input_frame, width=30)
        self.abbr_entry.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(input_frame, text="英文姓名（可选，中文自动转拼音）:").pack(anchor='w', padx=5, pady=2)
        self.full_entry = ttk.Entry(input_frame, width=30)
        self.full_entry.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(input_frame, text="添加作者", command=self.add_author).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(input_frame, text="批量导入", command=self.batch_import).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(input_frame, text="保存输入姓名", command=self.save_entered_common).pack(fill=tk.X, padx=5, pady=2)

        # 作者列表
        self.author_listbox = tk.Listbox(left_frame, width=45, height=20, font=('Arial', 10))
        self.author_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.author_listbox.bind('<Double-Button-1>', self.edit_author)
        
        # 顺序调整按钮
        order_frame = ttk.Frame(left_frame)
        order_frame.pack(fill=tk.X, pady=5)
        ttk.Label(order_frame, text="调整顺序:").pack(side=tk.LEFT, padx=5)
        ttk.Button(order_frame, text="↑ 上移", command=lambda: self.move_author(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(order_frame, text="↓ 下移", command=lambda: self.move_author(1)).pack(side=tk.LEFT, padx=2)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="编辑选中", command=self.edit_selected_author).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_author).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="清空全部", command=self.clear_authors).pack(side=tk.LEFT, padx=2)
        
        # 右侧框架
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        # 右侧使用PanedWindow，角色分配和输出结果可调整
        right_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)
        
        # 角色表格
        table_frame = ttk.LabelFrame(right_paned, text="角色分配", padding="10")
        right_paned.add(table_frame, weight=1)
        
        # 清空按钮框架
        clear_btn_frame = ttk.Frame(table_frame)
        clear_btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(clear_btn_frame, text="快速清空:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        
        # 作者清空按钮容器（使用Canvas支持滚动）
        btn_canvas = tk.Canvas(clear_btn_frame, height=35)
        btn_scrollbar = ttk.Scrollbar(clear_btn_frame, orient=tk.HORIZONTAL, command=btn_canvas.xview)
        self.clear_author_btn_frame = ttk.Frame(btn_canvas)
        
        btn_canvas.configure(xscrollcommand=btn_scrollbar.set)
        btn_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        btn_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        btn_canvas.create_window((0, 0), window=self.clear_author_btn_frame, anchor='nw')
        self.clear_author_btn_frame.bind('<Configure>', lambda e: btn_canvas.configure(scrollregion=btn_canvas.bbox('all')))
        
        ttk.Button(clear_btn_frame, text="清空全部勾选", command=self.clear_all_selections).pack(side=tk.RIGHT, padx=10)
        
        # 创建表格（增加行高以显示中英文，增大字体）
        style = ttk.Style()
        style.configure('Custom.Treeview', rowheight=36, font=('Microsoft YaHei UI', 13))
        style.configure('Custom.Treeview.Heading', font=('Microsoft YaHei UI', 13, 'bold'))
        
        self.tree = ttk.Treeview(table_frame, show='headings', height=6, style='Custom.Treeview')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 输出格式选择（固定在中间）
        format_frame = ttk.LabelFrame(right_frame, text="输出设置", padding="10")
        format_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(format_frame, text="期刊格式:").grid(row=0, column=0, padx=5)
        self.format_var = tk.StringVar(value="Elsevier")
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, 
                                      values=list(JOURNAL_FORMATS.keys()), state='readonly', width=18)
        self.format_combo.grid(row=0, column=1, padx=5)
        
        ttk.Button(format_frame, text="生成贡献声明", command=self.generate_contributions).grid(row=0, column=2, padx=10)
        ttk.Button(format_frame, text="添加新格式", command=self.add_new_format).grid(row=0, column=3, padx=5)
        ttk.Button(format_frame, text="删除格式", command=self.delete_format).grid(row=0, column=4, padx=5)
        ttk.Button(format_frame, text="导出 TXT", command=self.export_word).grid(row=0, column=5, padx=5)
        ttk.Button(format_frame, text="保存配置", command=self.save_data).grid(row=0, column=6, padx=5)
        ttk.Button(format_frame, text="加载配置", command=self.load_data).grid(row=0, column=7, padx=5)
        
        # 输出区域（可调整大小）
        output_frame = ttk.LabelFrame(right_paned, text="输出结果", padding="10")
        right_paned.add(output_frame, weight=1)
        
        self.output_text = tk.Text(output_frame, height=4, wrap=tk.WORD, font=('Arial', 10))
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(output_frame, text="复制到剪贴板", command=self.copy_to_clipboard).pack(pady=5)
        
    def move_author(self, direction):
        """移动作者顺序"""
        selection = self.author_listbox.curselection()
        if not selection:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Select an author to move' if self.language.get() == "English" else '请先选择要调整的作者'))
            return
            
        current_index = selection[0]
        new_index = current_index + direction
        
        if new_index < 0 or new_index >= len(self.author_order):
            return
            
        # 交换顺序
        self.author_order[current_index], self.author_order[new_index] = \
            self.author_order[new_index], self.author_order[current_index]
        
        self.update_author_list()
        self.update_table()
        
        # 重新选中
        self.author_listbox.selection_set(new_index)
        
    def add_author(self):
        abbr = self.abbr_entry.get().strip()
        full = self.full_entry.get().strip()
        
        full = self.resolve_name(abbr, full)
        abbr = abbr or full
        if not full:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Enter a Chinese or English name' if self.language.get() == "English" else '请填写中文或英文姓名'))
            return
            
        if abbr in self.authors:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('This author ID already exists; choose another ID' if self.language.get() == "English" else '该作者标识已存在，请使用不同的标识'))
            return
            
        # 自动生成作者英文缩写
        final_abbr = self.generate_pinyin_abbreviation(abbr, full)
        self.authors[abbr] = {'full': full, 'abbr': final_abbr}
        self.author_order.append(abbr)
        self.update_author_list()
        self.update_table()
        
        self.abbr_entry.delete(0, tk.END)
        self.full_entry.delete(0, tk.END)
        
    def edit_selected_author(self):
        self.edit_author(None)
        
    def edit_author(self, event):
        selection = self.author_listbox.curselection()
        if not selection:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Select an author to edit' if self.language.get() == "English" else '请先选择要编辑的作者'))
            return
            
        item_text = self.author_listbox.get(selection[0])
        parts = item_text.split(" | ")
        old_abbr = self.author_order[selection[0]]
        old_full = self.authors[old_abbr]['full']
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(('Edit author' if self.language.get() == "English" else '编辑作者'))
        edit_window.geometry("400x180")
        
        frame = ttk.Frame(edit_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="中文名 / 标识（可选）:").grid(row=0, column=0, padx=5, pady=10)
        abbr_entry = ttk.Entry(frame, width=30)
        abbr_entry.grid(row=0, column=1, padx=5)
        abbr_entry.insert(0, old_abbr)
        
        ttk.Label(frame, text="英文姓名（可选，中文自动转拼音）:").grid(row=1, column=0, padx=5, pady=10)
        full_entry = ttk.Entry(frame, width=30)
        full_entry.grid(row=1, column=1, padx=5)
        full_entry.insert(0, old_full)
        
        def save_edit():
            new_abbr = abbr_entry.get().strip()
            new_full = full_entry.get().strip()
            
            new_full = self.resolve_name(new_abbr, new_full)
            new_abbr = new_abbr or new_full
            if not new_full:
                messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Enter a name' if self.language.get() == "English" else '请填写完整信息'))
                return
                
            if new_abbr != old_abbr and new_abbr in self.authors:
                messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('This author ID already exists; choose another ID' if self.language.get() == "English" else '该作者标识已存在，请使用不同的标识'))
                return
                
            # 更新数据
            del self.authors[old_abbr]
            new_eng_abbr = self.generate_pinyin_abbreviation(new_abbr, new_full)
            self.authors[new_abbr] = {'full': new_full, 'abbr': new_eng_abbr}
            
            for values in self.role_vars.values():
                if old_abbr in values:
                    values[new_abbr] = values.pop(old_abbr)
            # 更新顺序列表
            idx = self.author_order.index(old_abbr)
            self.author_order[idx] = new_abbr
            
            self.update_author_list()
            self.update_table()
            edit_window.destroy()
            
        ttk.Button(frame, text=('Save' if self.language.get() == "English" else '保存'), command=save_edit).grid(row=2, column=0, columnspan=2, pady=10)
        
    def delete_author(self):
        selection = self.author_listbox.curselection()
        if not selection:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Select an author to delete' if self.language.get() == "English" else '请先选择要删除的作者'))
            return
            
        item_text = self.author_listbox.get(selection[0])
        abbr = self.author_order[selection[0]]
        del self.authors[abbr]
        for values in self.role_vars.values():
            values.pop(abbr, None)
        self.author_order.remove(abbr)
        self.update_author_list()
        self.update_table()
        
    def clear_authors(self):
        if messagebox.askyesno(('Confirm' if self.language.get() == "English" else '确认'), ('Clear all authors?' if self.language.get() == "English" else '确定清空所有作者？')):
            self.role_vars.clear()
            self.authors.clear()
            self.author_order.clear()
            self.update_author_list()
            self.update_table()
            
    def update_author_list(self):
        self.author_listbox.delete(0, tk.END)
        for abbr in self.author_order:
            author_data = self.authors[abbr]
            full = author_data['full'] if isinstance(author_data, dict) else author_data
            self.author_listbox.insert(tk.END, f"{abbr} | {full}")
            
    def update_table(self):
        # 清空表格
        self.tree.delete(*self.tree.get_children())
        previous = {role: {a: v.get() for a, v in values.items()} for role, values in self.role_vars.items()}
        self.role_vars.clear()
        
        # 设置列
        columns = ["角色"] + self.author_order
        self.tree['columns'] = columns
        
        # 设置列标题
        self.tree.heading("角色", text=("CRediT roles" if self.language.get() == "English" else "CRediT角色"))
        self.tree.column("角色", width=280)
        for abbr in self.author_order:
            self.tree.heading(abbr, text=abbr)
            self.tree.column(abbr, width=80, anchor='center')
        
        # 创建复选框变量
        for role_abbr, role_desc in CREDIT_ROLES:
            self.role_vars[role_abbr] = {}
            for abbr in self.author_order:
                self.role_vars[role_abbr][abbr] = tk.BooleanVar(value=previous.get(role_abbr, {}).get(abbr, False))
        
        # 添加角色行
        mode = self.display_mode.get()
        # Measure in pixels so text remains legible at different display scales.
        row_font = tkfont.Font(root=self.root, family="Microsoft YaHei UI", size=13)
        line_height = row_font.metrics("linespace")
        ttk.Style(self.root).configure(
            "Custom.Treeview",
            rowheight=line_height * (2 if mode == "both" else 1) + 8,
            font=("Microsoft YaHei UI", 13),
        )
        for role_abbr, role_desc in CREDIT_ROLES:
            if mode == "chinese":
                role_text = role_desc
            elif mode == "english":
                role_text = role_abbr
            else:  # both
                role_text = f"{role_abbr}\n{role_desc}"
            
            values = [role_text]
            for abbr in self.author_order:
                values.append("☑" if self.role_vars[role_abbr][abbr].get() else "☐")
            self.tree.insert('', tk.END, values=values)
        
        # 绑定点击事件
        self.tree.bind('<Button-1>', self.on_tree_click)
        
        # 更新清空按钮
        self.update_clear_buttons()
        
    def on_tree_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
            
        column = self.tree.identify_column(event.x)
        if column == '#1':  # 角色列
            return
            
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        # 获取角色和作者
        row_index = self.tree.index(item)
        role_abbr = CREDIT_ROLES[row_index][0]
        author_index = int(column[1:]) - 2
        author_abbr = self.author_order[author_index]
        
        # 切换选中状态
        var = self.role_vars[role_abbr][author_abbr]
        var.set(not var.get())
        
        # 更新显示
        self.tree.set(item, column, "☑" if var.get() else "☐")
        
    def clear_author_selections(self, author_abbr):
        """清空指定作者的所有勾选"""
        for role_abbr in self.role_vars:
            if author_abbr in self.role_vars[role_abbr]:
                self.role_vars[role_abbr][author_abbr].set(False)
        
        # 更新显示
        author_index = self.author_order.index(author_abbr)
        for i, item in enumerate(self.tree.get_children()):
            self.tree.set(item, f"#{author_index + 2}", "☐")
        
    def clear_all_selections(self):
        """清空所有勾选"""
        for role_abbr in self.role_vars:
            for abbr in self.role_vars[role_abbr]:
                self.role_vars[role_abbr][abbr].set(False)
        
        # 更新显示
        for i, item in enumerate(self.tree.get_children()):
            for j, abbr in enumerate(self.author_order):
                self.tree.set(item, f"#{j + 2}", "☐")
        
    def update_clear_buttons(self):
        """更新清空按钮"""
        # 清空旧按钮
        for widget in self.clear_author_btn_frame.winfo_children():
            widget.destroy()
        
        # 为每个作者创建清空按钮
        for abbr in self.author_order:
            btn = ttk.Button(self.clear_author_btn_frame, text=abbr, width=8,
                            command=lambda a=abbr: self.clear_author_selections(a))
            btn.pack(side=tk.LEFT, padx=2)
        
        # 更新滚动区域
        self.clear_author_btn_frame.update_idletasks()
        
    def batch_import(self):
        # 创建批量导入窗口
        import_window = tk.Toplevel(self.root)
        import_window.title(('Bulk import' if self.language.get() == "English" else '批量导入作者'))
        import_window.geometry("600x400")
        
        frame = ttk.Frame(import_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="每行一个作者：英文姓名，或 标识,英文姓名\n例如：\n张三,Zhang San\n李四,Li Si", 
                  justify=tk.LEFT).pack(anchor='w')
        
        text_widget = tk.Text(frame, height=15, width=60)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        def import_authors():
            text = text_widget.get('1.0', tk.END).strip()
            if not text:
                messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Enter author names' if self.language.get() == "English" else '请输入作者信息'))
                return
                
            count = 0
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                parts = [p.strip() for p in line.replace('，', ',').split(',', 1)]
                if len(parts) == 1:
                    parts = [parts[0], parts[0]]
                elif not parts[0]:
                    parts[0] = parts[1]
                if len(parts) >= 2:
                    abbr, full = parts[0], parts[1]
                    if full == abbr and any("\u4e00" <= c <= "\u9fff" for c in full):
                        full = ""
                    full = self.resolve_name(abbr, full)
                    if abbr and full and abbr not in self.authors:
                        eng_abbr = self.generate_pinyin_abbreviation(abbr, full)
                        self.authors[abbr] = {'full': full, 'abbr': eng_abbr}
                        self.author_order.append(abbr)
                        count += 1
            
            self.update_author_list()
            self.update_table()
            messagebox.showinfo(('Success' if self.language.get() == "English" else '成功'), f"成功导入 {count} 位作者")
            import_window.destroy()
            
        ttk.Button(btn_frame, text=('Import' if self.language.get() == "English" else '导入'), command=import_authors).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=('Cancel' if self.language.get() == "English" else '取消'), command=import_window.destroy).pack(side=tk.LEFT, padx=5)
        
    def generate_contributions(self):
        if not self.authors:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Add an author first' if self.language.get() == "English" else '请先添加作者'))
            return
            
        # 检查是否选择了角色
        has_selection = False
        for role_abbr in self.role_vars:
            for abbr in self.role_vars[role_abbr]:
                if self.role_vars[role_abbr][abbr].get():
                    has_selection = True
                    break
            if has_selection:
                break
        
        if not has_selection:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Select at least one contribution' if self.language.get() == "English" else '请至少选择一个角色'))
            return
        
        selected_format = self.format_var.get()
        format_config = JOURNAL_FORMATS.get(selected_format, {})
        format_type = 'role'
        abbr_config = None
        template = "{authors}: {role}."
        
        if isinstance(format_config, dict):
            format_type = format_config.get('type', 'author' if selected_format == "npj Digital Medicine" or selected_format.endswith("(按作者)") else 'role')
            template = format_config.get('template', template)
            abbr_config = format_config.get('abbr_config')
            if abbr_config is None and format_config.get('abbr_format'):
                abbr_config = self.map_old_abbr_format(format_config.get('abbr_format'))
        else:
            if selected_format == "npj Digital Medicine" or selected_format.endswith("(按作者)"):
                format_type = 'author'
            template = format_config if isinstance(format_config, str) and format_config != "author_abbrev" else template
        
        try:
            self.validate_template(template)
        except ValueError as exc:
            messagebox.showerror("模板错误", str(exc))
            return
        if format_type == 'author':
            output = []
            for abbr in self.author_order:
                author_roles = []
                for role_abbr, role_desc in CREDIT_ROLES:
                    if abbr in self.role_vars[role_abbr] and self.role_vars[role_abbr][abbr].get():
                        author_roles.append(role_abbr)
                if not author_roles:
                    continue
                author_data = self.authors[abbr]
                if isinstance(author_data, dict):
                    abbrev = self.format_author_abbreviation(abbr, author_data['full'], abbr_config)
                else:
                    abbrev = self.format_author_abbreviation(abbr, author_data, abbr_config)
                output.append(template.format(authors=abbrev, role=', '.join(author_roles)))
            self.output_text.delete('1.0', tk.END)
            self.output_text.insert('1.0', "\n".join(output))
            return
        
        # 其他格式：按角色列出作者
        role_authors = {}
        for role_abbr, role_desc in CREDIT_ROLES:
            authors_for_role = []
            for abbr in self.role_vars[role_abbr]:
                if self.role_vars[role_abbr][abbr].get():
                    author_data = self.authors[abbr]
                    if isinstance(author_data, dict):
                        if abbr_config:
                            authors_for_role.append(self.format_author_abbreviation(abbr, author_data['full'], abbr_config))
                        else:
                            authors_for_role.append(author_data['full'])
                    else:
                        if abbr_config:
                            authors_for_role.append(self.format_author_abbreviation(abbr, author_data, abbr_config))
                        else:
                            authors_for_role.append(author_data)
            if authors_for_role:
                role_authors[role_abbr] = authors_for_role
        
        # 生成文本
        output = []
        format_template = template
        for role_abbr, authors in role_authors.items():
            if len(authors) == 1:
                author_str = authors[0]
            elif len(authors) == 2:
                author_str = f"{authors[0]} and {authors[1]}"
            else:
                author_str = ", ".join(authors[:-1]) + f", and {authors[-1]}"
            output.append(format_template.format(authors=author_str, role=role_abbr))
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert('1.0', "\n".join(output))
        
    @staticmethod
    def validate_template(template):
        if not isinstance(template, str) or len(template) > 10000:
            raise ValueError("模板必须是长度不超过 10000 的文本")
        fields = set()
        for _, field, spec, conversion in Formatter().parse(template):
            if field is not None:
                if field not in {"authors", "role"} or spec or conversion:
                    raise ValueError("仅支持 {authors} 和 {role}，不支持其他字段或格式修饰")
                fields.add(field)
        if fields != {"authors", "role"}:
            raise ValueError("模板必须同时包含 {authors} 和 {role}")
        return template

    def generate_pinyin_abbreviation(self, chinese_name, english_name):
        """根据中文名字识别拼音首字母，默认使用 C.Z. 格式"""
        initials = self.get_chinese_initials(chinese_name)
        
        # 如果识别了至少2个字母，组成默认缩写
        if len(initials) >= 2:
            return '.'.join(initials) + '.'
        elif len(initials) == 1:
            return initials[0] + '.'
        else:
            # 退化到英文名处理
            parts = re.findall(r"[^\W\d_]+", english_name, re.UNICODE)
            if len(parts) >= 2:
                return f"{parts[0][0]}.{parts[-1][0]}."
            elif len(parts) == 1:
                return f"{parts[0][0]}."
            else:
                return "?"
    
    def format_author_abbreviation(self, chinese_name, english_name, abbr_config=None):
        """根据指定格式或配置生成作者缩写"""
        # 兼容旧的字符串类型格式
        if isinstance(abbr_config, str) or abbr_config is None:
            format_type = abbr_config if isinstance(abbr_config, str) else 'name_surname'
            initials = self.get_chinese_initials(chinese_name)
            if len(initials) < 2:
                parts = re.findall(r"[^\W\d_]+", english_name, re.UNICODE)
                if len(parts) >= 2:
                    initials = [parts[0][0].upper(), parts[-1][0].upper()]
                elif len(parts) == 1:
                    initials = [parts[0][0].upper()]
            if format_type == 'name_surname':
                if len(initials) >= 2:
                    return f"{initials[0]}.{initials[-1]}."
                return '.'.join(initials) + '.' if initials else '?'
            elif format_type == 'surname_name':
                if len(initials) >= 2:
                    return f"{initials[-1]}.{initials[0]}."
                return '.'.join(initials) + '.' if initials else '?'
            elif format_type == 'full_name':
                if initials:
                    return '.'.join(initials) + '.'
                return '?'
            elif format_type == 'full_name_reverse':
                if len(initials) >= 2:
                    reversed_initials = [initials[-1]] + initials[:-1]
                    return '.'.join(reversed_initials) + '.'
                return '.'.join(initials) + '.' if initials else '?'
            elif format_type == 'no_dots':
                if len(initials) >= 2:
                    return f"{initials[0]}{initials[-1]}"
                return ''.join(initials) if initials else '?'
            elif format_type == 'no_dots_full':
                return ''.join(initials) if initials else '?'
            elif format_type == 'full_name_pinyin':
                if initials:
                    return '.'.join(initials) + '.'
                return '?'
            if len(initials) >= 2:
                return f"{initials[0]}.{initials[-1]}."
            return '.'.join(initials) + '.' if initials else '?'
        
        # 新的配置结构
        initials = self.get_chinese_initials(chinese_name)
        if len(initials) < 2:
            parts = re.findall(r"[^\W\d_]+", english_name, re.UNICODE)
            if len(parts) >= 2:
                initials = [parts[0][0].upper(), parts[-1][0].upper()]
            elif len(parts) == 1:
                initials = [parts[0][0].upper()]
        if not initials:
            return '?'
        use_dots = abbr_config.get('dots', True)
        order_2char = abbr_config.get('order_2char', 'YZ')
        order_3char = abbr_config.get('order_3char', 'QSH')
        selected = initials
        if len(initials) == 2:
            if order_2char == 'ZY':
                selected = [initials[1], initials[0]]
            else:
                selected = [initials[0], initials[1]]
        elif len(initials) == 3:
            if order_3char == 'SHQ':
                selected = [initials[1], initials[2], initials[0]]
            elif order_3char == 'QS':
                selected = [initials[0], initials[1]]
            elif order_3char == 'SQ':
                selected = [initials[1], initials[0]]
            else:
                selected = initials
        else:
            if order_3char == 'SHQ':
                selected = initials[1:] + [initials[0]]
            elif order_3char == 'QS':
                selected = initials[:2]
            elif order_3char == 'SQ':
                selected = [initials[1], initials[0]] if len(initials) > 1 else initials
            else:
                selected = initials
        if use_dots:
            return '.'.join(selected) + '.'
        return ''.join(selected)
    
    def map_old_abbr_format(self, old_format):
        """将旧版缩写格式映射到新的点/顺序配置"""
        mapping = {
            'name_surname': {'dots': True, 'order_2char': 'YZ', 'order_3char': 'QS'},
            'surname_name': {'dots': True, 'order_2char': 'ZY', 'order_3char': 'SQ'},
            'full_name': {'dots': True, 'order_2char': 'YZ', 'order_3char': 'QSH'},
            'full_name_reverse': {'dots': True, 'order_2char': 'ZY', 'order_3char': 'SHQ'},
            'no_dots': {'dots': False, 'order_2char': 'YZ', 'order_3char': 'QS'},
            'no_dots_full': {'dots': False, 'order_2char': 'YZ', 'order_3char': 'QSH'},
            'full_name_pinyin': {'dots': True, 'order_2char': 'YZ', 'order_3char': 'QSH'}
        }
        return mapping.get(old_format, {'dots': True, 'order_2char': 'YZ', 'order_3char': 'QSH'})
    
    def get_chinese_initials(self, chinese_name):
        """获取中文名的拼音首字母列表"""
        # 拼音首字母映射表
        pinyin_map = {
            # 常见姓氏
            '赵': 'Z', '钱': 'Q', '孙': 'S', '李': 'L', '周': 'Z', '吴': 'W', '郑': 'Z', '王': 'W',
            '冯': 'F', '陈': 'C', '褚': 'C', '卫': 'W', '蒋': 'J', '沈': 'S', '韩': 'H', '杨': 'Y',
            '朱': 'Z', '秦': 'Q', '尤': 'Y', '许': 'X', '何': 'H', '吕': 'L', '施': 'S', '张': 'Z',
            '孔': 'K', '曹': 'C', '严': 'Y', '华': 'H', '金': 'J', '魏': 'W', '陶': 'T', '姜': 'J',
            '戚': 'Q', '谢': 'X', '邹': 'Z', '喻': 'Y', '柏': 'B', '水': 'S', '窦': 'D', '章': 'Z',
            '云': 'Y', '苏': 'S', '潘': 'P', '葛': 'G', '奚': 'X', '范': 'F', '彭': 'P', '郎': 'L',
            '鲁': 'L', '韦': 'W', '昌': 'C', '马': 'M', '苗': 'M', '凤': 'F', '花': 'H', '方': 'F',
            '俞': 'Y', '任': 'R', '袁': 'Y', '柳': 'L', '酆': 'F', '鲍': 'B', '史': 'S', '唐': 'T',
            '费': 'F', '廉': 'L', '岑': 'C', '薛': 'X', '雷': 'L', '贺': 'H', '倪': 'N', '汤': 'T',
            '滕': 'T', '殷': 'Y', '罗': 'L', '毕': 'B', '郝': 'H', '邬': 'W', '安': 'A', '常': 'C',
            '乐': 'L', '于': 'Y', '时': 'S', '傅': 'F', '皮': 'P', '卞': 'B', '齐': 'Q', '康': 'K',
            '伍': 'W', '余': 'Y', '元': 'Y', '卜': 'B', '顾': 'G', '孟': 'M', '平': 'P', '黄': 'H',
            '和': 'H', '穆': 'M', '萧': 'X', '尹': 'Y', '姚': 'Y', '邵': 'S', '湛': 'Z', '汪': 'W',
            '祁': 'Q', '毛': 'M', '禹': 'Y', '狄': 'D', '米': 'M', '贝': 'B', '明': 'M', '臧': 'Z',
            '计': 'J', '伏': 'F', '成': 'C', '戴': 'D', '谈': 'T', '宋': 'S', '茅': 'M', '庞': 'P',
            '熊': 'X', '纪': 'J', '舒': 'S', '屈': 'Q', '项': 'X', '祝': 'Z', '董': 'D', '梁': 'L',
            '杜': 'D', '阮': 'R', '蓝': 'L', '闵': 'M', '席': 'X', '季': 'J', '麻': 'M', '强': 'Q',
            '贾': 'J', '路': 'L', '娄': 'L', '危': 'W', '江': 'J', '童': 'T', '颜': 'Y', '郭': 'G',
            '梅': 'M', '盛': 'S', '林': 'L', '刁': 'D', '钟': 'Z', '徐': 'X', '邱': 'Q', '骆': 'L',
            '高': 'G', '夏': 'X', '蔡': 'C', '田': 'T', '樊': 'F', '胡': 'H', '凌': 'L', '霍': 'H',
            '虞': 'Y', '万': 'W', '支': 'Z', '柯': 'K', '昝': 'Z', '管': 'G', '卢': 'L', '莫': 'M',
            '经': 'J', '房': 'F', '裘': 'Q', '缪': 'M', '干': 'G', '解': 'X', '应': 'Y', '宗': 'Z',
            '丁': 'D', '宣': 'X', '贲': 'B', '邓': 'D', '郁': 'Y', '单': 'S', '杭': 'H', '洪': 'H',
            '包': 'B', '诸': 'Z', '左': 'Z', '石': 'S', '崔': 'C', '吉': 'J', '钮': 'N', '龚': 'G',
            '程': 'C', '嵇': 'J', '邢': 'X', '滑': 'H', '裴': 'P', '陆': 'L', '荣': 'R', '翁': 'W',
            '荀': 'X', '羊': 'Y', '甄': 'Z', '家': 'J', '封': 'F', '芮': 'R', '羿': 'Y', '储': 'C',
            '靳': 'J', '汲': 'J', '邴': 'B', '糜': 'M', '松': 'S', '井': 'J', '段': 'D', '富': 'F',
            '巫': 'W', '乌': 'W', '焦': 'J', '巴': 'B', '弓': 'G', '牧': 'M', '隗': 'W', '山': 'S',
            '谷': 'G', '车': 'C', '侯': 'H', '宓': 'M', '蓬': 'P', '全': 'Q', '郗': 'X', '班': 'B',
            '仰': 'Y', '秋': 'Q', '仲': 'Z', '伊': 'I', '宫': 'G', '宁': 'N', '仇': 'Q', '栾': 'L',
            '暴': 'B', '甘': 'G', '钭': 'T', '厉': 'L', '戎': 'R', '祖': 'Z', '武': 'W', '符': 'F',
            '刘': 'L', '景': 'J', '詹': 'Z', '龙': 'L', '叶': 'Y', '幸': 'X', '司': 'S', '韶': 'S',
            '郜': 'G', '黎': 'L', '蓟': 'J', '薄': 'B', '印': 'Y', '宿': 'S', '白': 'B', '怀': 'H',
            '蒲': 'P', '台': 'T', '丛': 'C', '鄂': 'E', '索': 'S', '咸': 'X', '籍': 'J', '赖': 'L',
            '卓': 'Z', '蔺': 'L', '屠': 'T', '蒙': 'M', '池': 'C', '乔': 'Q', '阴': 'Y', '郁': 'Y',
            '胥': 'X', '能': 'N', '苍': 'C', '双': 'S', '闻': 'W', '莘': 'S', '党': 'D', '翟': 'Z',
            '谭': 'T', '贡': 'G', '劳': 'L', '逄': 'P', '姬': 'J', '申': 'S', '扶': 'F', '堵': 'D',
            '冉': 'R', '宰': 'Z', '郦': 'L', '雍': 'Y', '却': 'Q', '璩': 'Q', '桑': 'S', '桂': 'G',
            '濮': 'P', '牛': 'N', '寿': 'S', '通': 'T', '边': 'B', '扈': 'H', '燕': 'Y', '冀': 'J',
            '郏': 'J', '浦': 'P', '尚': 'S', '农': 'N', '温': 'W', '别': 'B', '庄': 'Z', '晏': 'Y',
            '柴': 'C', '瞿': 'Q', '阎': 'Y', '充': 'C', '慕': 'M', '连': 'L', '茹': 'R', '习': 'X',
            '宦': 'H', '艾': 'A', '鱼': 'Y', '容': 'R', '向': 'X', '古': 'G', '易': 'Y', '慎': 'S',
            '戈': 'G', '廖': 'L', '庾': 'Y', '终': 'Z', '暨': 'J', '居': 'J', '衡': 'H', '步': 'B',
            '都': 'D', '耿': 'G', '满': 'M', '弘': 'H', '匡': 'K', '国': 'G', '文': 'W', '寇': 'K',
            '广': 'G', '禄': 'L', '阙': 'Q', '东': 'D', '欧': 'O', '殳': 'S', '沃': 'W', '利': 'L',
            '蔚': 'W', '越': 'Y', '夔': 'K', '隆': 'L', '师': 'S', '巩': 'G', '厍': 'S', '聂': 'N',
            '晁': 'C', '勾': 'G', '敖': 'A', '融': 'R', '冷': 'L', '訾': 'Z', '辛': 'X', '阚': 'K',
            '那': 'N', '简': 'J', '饶': 'R', '空': 'K', '曾': 'Z', '毋': 'W', '沙': 'S', '乜': 'N',
            '养': 'Y', '鞠': 'J', '须': 'X', '丰': 'F', '巢': 'C', '关': 'G', '蒯': 'K', '相': 'X',
            '查': 'Z', '后': 'H', '荆': 'J', '红': 'H', '游': 'Y', '竺': 'Z', '权': 'Q', '逯': 'L',
            '盖': 'G', '益': 'Y', '桓': 'H', '公': 'G',
            # 常见名字用字
            '伟': 'W', '芳': 'F', '娜': 'N', '敏': 'M', '静': 'J', '丽': 'L', '强': 'Q', '磊': 'L',
            '军': 'J', '洋': 'Y', '勇': 'Y', '艳': 'Y', '杰': 'J', '娟': 'J', '涛': 'T', '明': 'M',
            '超': 'C', '秀': 'X', '霞': 'X', '平': 'P', '刚': 'G', '桂': 'G', '英': 'Y', '华': 'H',
            '慧': 'H', '建': 'J', '红': 'H', '文': 'W', '玲': 'L', '辉': 'H', '斌': 'B', '宇': 'Y',
            '鹏': 'P', '浩': 'H', '凯': 'K', '毅': 'Y', '清': 'Q', '林': 'L', '梅': 'M', '琴': 'Q',
            '博': 'B', '晨': 'C', '欣': 'X', '威': 'W', '佳': 'J', '昊': 'H', '雪': 'X', '锋': 'F',
            '婷': 'T', '萍': 'P', '飞': 'F', '帆': 'F', '莉': 'L', '阳': 'Y', '翔': 'X', '琦': 'Q',
            '勤': 'Q', '乐': 'L', '旭': 'X', '瑜': 'Y', '璐': 'L', '颖': 'Y', '倩': 'Q', '蕾': 'L',
            '瑶': 'Y', '薇': 'W', '晶': 'J', '瑛': 'Y', '妍': 'Y', '岚': 'L', '馨': 'X', '琪': 'Q',
            '彤': 'T', '菲': 'F', '媛': 'Y', '楠': 'N', '怡': 'Y', '梦': 'M', '琳': 'L', '丹': 'D',
            '玉': 'Y', '燕': 'Y', '兰': 'L', '凤': 'F', '云': 'Y', '洁': 'J', '瑞': 'R', '龙': 'L',
            '东': 'D', '峰': 'F', '波': 'B', '兵': 'B', '亮': 'L', '健': 'J', '坤': 'K', '恒': 'H',
            '俊': 'J', '豪': 'H', '皓': 'H', '然': 'R', '轩': 'X', '奕': 'Y', '霖': 'L', '天': 'T',
            '贤': 'X', '宁': 'N', '岩': 'Y', '松': 'S', '德': 'D', '诚': 'C', '远': 'Y', '航': 'H',
            '铭': 'M', '哲': 'Z', '睿': 'R', '祥': 'X', '晓': 'X', '春': 'C', '海': 'H', '山': 'S',
            '河': 'H', '江': 'J', '湖': 'H', '月': 'Y', '星': 'X', '雨': 'Y', '电': 'D', '花': 'H',
            '草': 'C', '树': 'S', '木': 'M', '银': 'Y', '铜': 'T', '铁': 'T', '钢': 'G', '宝': 'B',
            '珍': 'Z', '珠': 'Z', '瑾': 'J', '璇': 'X', '霞': 'X', '秀': 'X', '聪': 'C', '慧': 'H',
            '学': 'X', '思': 'S', '萱': 'X', '诗': 'S', '涵': 'H', '雅': 'Y', '晗': 'H', '凝': 'N',
            '熙': 'X', '子': 'Z', '一': 'Y', '二': 'E', '三': 'S', '四': 'S', '五': 'W', '六': 'L',
            '七': 'Q', '八': 'B', '九': 'J', '十': 'S', '百': 'B', '千': 'Q', '万': 'W', '亿': 'Y',
            '京': 'J', '垓': 'G', '秭': 'Z', '穰': 'R', '沟': 'G', '涧': 'J', '正': 'Z', '载': 'Z',
            '极': 'J', '分': 'F', '厘': 'L', '毫': 'H', '微': 'W', '纤': 'X', '尘': 'C', '埃': 'A',
            '渺': 'M', '漠': 'M', '卫': 'W', '徐': 'X', '邱': 'Q', '骆': 'L', '高': 'G', '夏': 'X',
            '蔡': 'C', '田': 'T', '樊': 'F', '胡': 'H', '凌': 'L', '霍': 'H', '虞': 'Y', '支': 'Z',
            '柯': 'K', '昝': 'Z', '管': 'G', '卢': 'L', '莫': 'M', '经': 'J', '房': 'F', '裘': 'Q',
            '缪': 'M', '干': 'G', '解': 'X', '应': 'Y', '宗': 'Z', '丁': 'D', '宣': 'X', '贲': 'B',
            '邓': 'D', '单': 'S', '杭': 'H', '洪': 'H', '包': 'B', '诸': 'Z', '左': 'Z', '石': 'S',
            '崔': 'C', '吉': 'J', '钮': 'N', '龚': 'G', '程': 'C', '嵇': 'J', '邢': 'X', '滑': 'H',
            '裴': 'P', '荣': 'R', '翁': 'W', '荀': 'X', '羊': 'Y', '甄': 'Z', '家': 'J', '封': 'F',
            '芮': 'R', '羿': 'Y', '储': 'C', '靳': 'J', '汲': 'J', '邴': 'B', '糜': 'M', '井': 'J',
            '段': 'D', '富': 'F', '巫': 'W', '乌': 'W', '焦': 'J', '巴': 'B', '弓': 'G', '牧': 'M',
            '隗': 'W', '谷': 'G', '车': 'C', '侯': 'H', '宓': 'M', '蓬': 'P', '全': 'Q', '郗': 'X',
            '班': 'B', '仰': 'Y', '秋': 'Q', '仲': 'Z', '伊': 'I', '宫': 'G', '仇': 'Q', '栾': 'L',
            '暴': 'B', '甘': 'G', '钭': 'T', '厉': 'L', '戎': 'R', '祖': 'Z', '符': 'F', '刘': 'L',
            '景': 'J', '詹': 'Z', '叶': 'Y', '幸': 'X', '司': 'S', '韶': 'S', '郜': 'G', '黎': 'L',
            '蓟': 'J', '薄': 'B', '印': 'Y', '宿': 'S', '白': 'B', '怀': 'H', '蒲': 'P', '台': 'T',
            '丛': 'C', '鄂': 'E', '索': 'S', '咸': 'X', '籍': 'J', '赖': 'L', '卓': 'Z', '蔺': 'L',
            '屠': 'T', '蒙': 'M', '池': 'C', '乔': 'Q', '阴': 'Y', '胥': 'X', '能': 'N', '苍': 'C',
            '双': 'S', '闻': 'W', '莘': 'S', '党': 'D', '翟': 'Z', '谭': 'T', '贡': 'G', '劳': 'L',
            '逄': 'P', '姬': 'J', '申': 'S', '扶': 'F', '堵': 'D', '冉': 'R', '宰': 'Z', '郦': 'L',
            '雍': 'Y', '却': 'Q', '璩': 'Q', '桑': 'S', '桂': 'G', '濮': 'P', '牛': 'N', '寿': 'S',
            '通': 'T', '边': 'B', '扈': 'H', '燕': 'Y', '冀': 'J', '郏': 'J', '浦': 'P', '尚': 'S',
            '农': 'N', '温': 'W', '别': 'B', '庄': 'Z', '晏': 'Y', '柴': 'C', '瞿': 'Q', '阎': 'Y',
            '充': 'C', '慕': 'M', '连': 'L', '茹': 'R', '习': 'X', '宦': 'H', '艾': 'A', '鱼': 'Y',
            '容': 'R', '向': 'X', '古': 'G', '易': 'Y', '慎': 'S', '戈': 'G', '廖': 'L', '庾': 'Y',
            '终': 'Z', '暨': 'J', '居': 'J', '衡': 'H', '步': 'B', '都': 'D', '耿': 'G', '满': 'M',
            '弘': 'H', '匡': 'K', '国': 'G', '寇': 'K', '广': 'G', '禄': 'L', '阙': 'Q', '欧': 'O',
            '殳': 'S', '沃': 'W', '利': 'L', '蔚': 'W', '越': 'Y', '夔': 'K', '隆': 'L', '师': 'S',
            '巩': 'G', '厍': 'S', '聂': 'N', '晁': 'C', '勾': 'G', '敖': 'A', '融': 'R', '冷': 'L',
            '訾': 'Z', '辛': 'X', '阚': 'K', '那': 'N', '简': 'J', '饶': 'R', '空': 'K', '曾': 'Z',
            '毋': 'W', '沙': 'S', '乜': 'N', '养': 'Y', '鞠': 'J', '须': 'X', '丰': 'F', '巢': 'C',
            '关': 'G', '蒯': 'K', '相': 'X', '查': 'Z', '后': 'H', '荆': 'J', '游': 'Y', '竺': 'Z',
            '权': 'Q', '逯': 'L', '盖': 'G', '益': 'Y', '桓': 'H', '公': 'G',
        }
        
        if not any("\u4e00" <= ch <= "\u9fff" for ch in chinese_name):
            return []
        initials = []
        for char in chinese_name:
            if char in pinyin_map:
                initials.append(pinyin_map[char])
            elif char.isascii() and char.isalpha():
                initials.append(char.upper())
        
        return initials if len(initials) == len(chinese_name) else []
    
    def add_new_format(self):
        """添加新的期刊格式"""
        add_window = tk.Toplevel(self.root)
        add_window.title(("New template" if self.language.get() == "English" else "添加新期刊格式"))
        add_window.geometry("750x650")
        add_window.minsize(750, 650)
        
        container = ttk.Frame(add_window)
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, borderwidth=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', _on_mousewheel)
        
        frame = ttk.Frame(scrollable_frame, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 说明
        ttk.Label(frame, text=("New template" if self.language.get() == "English" else "添加新期刊格式"), font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # 格式类型选择
        type_frame = ttk.LabelFrame(frame, text=("Grouping" if self.language.get() == "English" else "选择格式类型"), padding="10")
        type_frame.pack(fill=tk.X, pady=10)
        
        format_type = tk.StringVar(value="author")
        ttk.Radiobutton(type_frame, text=("By author (e.g. Z.S.: Conceptualization, Methodology.)" if self.language.get() == "English" else "按作者列出角色（如：Z.S.: Conceptualization, Methodology.）"), 
                       variable=format_type, value="author").pack(anchor='w', pady=2)
        ttk.Radiobutton(type_frame, text=("By role (e.g. Zhang San and Li Si: Conceptualization.)" if self.language.get() == "English" else "按角色列出作者（如：Zhang San and Li Si: Conceptualization.）"), 
                       variable=format_type, value="role").pack(anchor='w', pady=2)
        
        # 作者缩写格式选择
        abbr_format_frame = ttk.LabelFrame(frame, text=("Author initials" if self.language.get() == "English" else "作者缩写格式"), padding="10")
        abbr_format_frame.pack(fill=tk.X, pady=10)
        
        abbr_separator = tk.StringVar(value="with")
        ttk.Label(abbr_format_frame, text=("Initial separators:" if self.language.get() == "English" else "是否使用点分隔:")).pack(anchor='w', pady=(0, 5))
        ttk.Radiobutton(abbr_format_frame, text=("With periods (Z.S.)" if self.language.get() == "English" else "有点分隔（如 Z.S.）"), variable=abbr_separator, value="with").pack(anchor='w', pady=1)
        ttk.Radiobutton(abbr_format_frame, text=("Without periods (ZS)" if self.language.get() == "English" else "无点分隔（如 ZS）"), variable=abbr_separator, value="without").pack(anchor='w', pady=1)
        
        ttk.Separator(abbr_format_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        abbr_2char_order = tk.StringVar(value="YZ")
        ttk.Label(abbr_format_frame, text=("Two-character Chinese names (e.g. Ying Zheng):" if self.language.get() == "English" else "两个字中文名缩写顺序（示例：嬴政）:")).pack(anchor='w', pady=(0, 5))
        ttk.Radiobutton(abbr_format_frame, text=("Y Z (family + given)" if self.language.get() == "English" else "Y Z（姓+名）"), variable=abbr_2char_order, value="YZ").pack(anchor='w', pady=1)
        ttk.Radiobutton(abbr_format_frame, text=("Z Y (given + family)" if self.language.get() == "English" else "Z Y（名+姓）"), variable=abbr_2char_order, value="ZY").pack(anchor='w', pady=1)
        
        ttk.Separator(abbr_format_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        abbr_3char_order = tk.StringVar(value="QSH")
        ttk.Label(abbr_format_frame, text=("Three-character Chinese names (e.g. Qin Shi Huang):" if self.language.get() == "English" else "三个字中文名缩写顺序（示例：秦始皇）:")).pack(anchor='w', pady=(0, 5))
        ttk.Radiobutton(abbr_format_frame, text=("QSH (family + both given initials)" if self.language.get() == "English" else "QSH（姓+名+名）"), variable=abbr_3char_order, value="QSH").pack(anchor='w', pady=1)
        ttk.Radiobutton(abbr_format_frame, text=("SHQ (both given initials + family)" if self.language.get() == "English" else "SHQ（名+名+姓）"), variable=abbr_3char_order, value="SHQ").pack(anchor='w', pady=1)
        ttk.Radiobutton(abbr_format_frame, text=("QS (family + first given initial)" if self.language.get() == "English" else "QS（姓+名首字母）"), variable=abbr_3char_order, value="QS").pack(anchor='w', pady=1)
        ttk.Radiobutton(abbr_format_frame, text=("SQ (first given initial + family)" if self.language.get() == "English" else "SQ（名首字母+姓）"), variable=abbr_3char_order, value="SQ").pack(anchor='w', pady=1)
        
        # 期刊名称
        name_frame = ttk.Frame(frame)
        name_frame.pack(fill=tk.X, pady=10)
        ttk.Label(name_frame, text=("Template name:" if self.language.get() == "English" else "期刊名称:")).pack(side=tk.LEFT, padx=5)
        format_name_entry = ttk.Entry(name_frame, width=40)
        format_name_entry.pack(side=tk.LEFT, padx=5)
        
        # 自定义模板（可选）
        template_frame = ttk.LabelFrame(frame, text=("Template (optional; blank uses default)" if self.language.get() == "English" else "自定义模板（可选，留空使用默认）"), padding="10")
        template_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(template_frame, text=("Use {authors} for names and {role} for contributions" if self.language.get() == "English" else "使用 {authors} 代表作者，{role} 代表角色")).pack(anchor='w')
        ttk.Label(template_frame, text=("Example: {authors} contributed to {role}." if self.language.get() == "English" else "示例：{authors} contributed to {role}.")).pack(anchor='w', pady=(0,5))
        
        template_entry = ttk.Entry(template_frame, width=50)
        template_entry.pack(fill=tk.X, pady=5)
        template_entry.insert(0, "{authors}: {role}.")
        
        # 示例粘贴区
        example_frame = ttk.LabelFrame(frame, text=("Paste an example statement to detect grouping" if self.language.get() == "English" else "粘贴该期刊的作者贡献示例（用于识别格式）"), padding="10")
        example_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        text_widget = tk.Text(example_frame, height=6, font=('Arial', 9))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 预览区
        preview_frame = ttk.LabelFrame(frame, text=("Preview" if self.language.get() == "English" else "输出预览"), padding="10")
        preview_frame.pack(fill=tk.X, pady=10)
        
        preview_label = ttk.Label(preview_frame, text=("Select a grouping and enter a template to preview" if self.language.get() == "English" else "选择格式类型和输入模板后会显示预览"), justify=tk.LEFT, wraplength=700)
        preview_label.pack(anchor='w')
        
        # 识别结果显示区
        result_frame = ttk.LabelFrame(frame, text=("Detection result" if self.language.get() == "English" else "识别结果"), padding="10")
        result_frame.pack(fill=tk.X, pady=10)
        
        result_label = ttk.Label(result_frame, text=("Click Detect grouping to see a suggestion" if self.language.get() == "English" else "点击“识别格式”按钮会在此显示结果"), justify=tk.LEFT, foreground='blue')
        result_label.pack(anchor='w')
        
        def update_preview(*args):
            selected_type = format_type.get()
            template = template_entry.get().strip()
            try:
                self.validate_template(template or "{authors}: {role}.")
            except ValueError as exc:
                preview_label.config(text=("Use both {authors} and {role}; other fields and format modifiers are unsupported." if self.language.get() == "English" else str(exc)))
                return
            use_dots = abbr_separator.get() == 'with'
            order2 = abbr_2char_order.get()
            order3 = abbr_3char_order.get()
            
            def format_example(initials):
                if len(initials) == 2 and order2 == 'ZY':
                    initials = [initials[1], initials[0]]
                if len(initials) == 3:
                    if order3 == 'SHQ':
                        initials = [initials[1], initials[2], initials[0]]
                    elif order3 == 'QS':
                        initials = [initials[0], initials[1]]
                    elif order3 == 'SQ':
                        initials = [initials[1], initials[0]]
                if use_dots:
                    return '.'.join(initials) + '.'
                return ''.join(initials)
            
            example2 = format_example(['Y', 'Z'])
            example3 = format_example(['Q', 'S', 'H'])
            
            if selected_type == "author":
                preview = (f"Preview (by author):\n\n{example2}: Conceptualization, Methodology.\n{example3}: Writing – original draft." if self.language.get() == "English" else f"预览效果（按作者列出角色）：\n\n{example2}: Conceptualization, Methodology.\n{example3}: Writing – original draft.")
            else:
                if not template:
                    template = "{authors}: {role}."
                preview = (f"Preview (by role):\n\n{template.format(authors='Zhang San and Li Si', role='Conceptualization')}" if self.language.get() == "English" else f"预览效果（按角色列出作者）：\n\n{template.format(authors='Zhang San and Li Si', role='Conceptualization')}")
            
            preview_label.config(text=preview)
        
        format_type.trace('w', update_preview)
        abbr_separator.trace('w', update_preview)
        abbr_2char_order.trace('w', update_preview)
        abbr_3char_order.trace('w', update_preview)
        template_entry.bind('<KeyRelease>', update_preview)
        
        def save_format():
            format_name = format_name_entry.get().strip()
            if not format_name:
                messagebox.showwarning(("Warning" if self.language.get() == "English" else "警告"), ("Enter a template name" if self.language.get() == "English" else "请输入期刊名称"))
                return
            
            selected_type = format_type.get()
            template = template_entry.get().strip() or "{authors}: {role}."
            try:
                self.validate_template(template)
            except ValueError as exc:
                messagebox.showerror(("Invalid template" if self.language.get() == "English" else "模板错误"), ("Use both {authors} and {role}; other fields and format modifiers are unsupported." if self.language.get() == "English" else str(exc)))
                return
            abbr_options = {
                'dots': abbr_separator.get() == 'with',
                'order_2char': abbr_2char_order.get(),
                'order_3char': abbr_3char_order.get()
            }
            
            if selected_type == "author":
                format_name_with_suffix = format_name + "(按作者)"
                JOURNAL_FORMATS[format_name_with_suffix] = {
                    'type': 'author',
                    'template': template or "{authors}: {role}.",
                    'abbr_config': abbr_options
                }
                
                if self.format_combo:
                    self.format_combo['values'] = list(JOURNAL_FORMATS.keys())
                self.save_custom_formats()
                
                dot_text = ('with periods' if self.language.get() == "English" else '有点分隔') if abbr_options['dots'] else ('without periods' if self.language.get() == "English" else '无点分隔')
                order2_text = 'Y Z' if abbr_options['order_2char'] == 'YZ' else 'Z Y'
                order3_text = abbr_options['order_3char']
                messagebox.showinfo(("Success" if self.language.get() == "English" else "成功"), (f"Template added: {format_name}\n\nGrouping: by author\nInitials: {dot_text}, two-character order {order2_text}, three-character order {order3_text}" if self.language.get() == "English" else f"已添加格式：{format_name}\n\n格式类型：按作者列出角色\n缩写格式：{dot_text}，两个字顺序 {order2_text}，三个字顺序 {order3_text}"))

                add_window.destroy()
            else:
                # 按角色格式
                if not template:
                    template = "{authors}: {role}."
                
                JOURNAL_FORMATS[format_name] = template
                
                # 更新下拉框
                if self.format_combo:
                    self.format_combo['values'] = list(JOURNAL_FORMATS.keys())
                
                # 保存到文件
                self.save_custom_formats()
                
                messagebox.showinfo(("Success" if self.language.get() == "English" else "成功"), (f"Template added: {format_name}\n\nGrouping: by role\nTemplate: {template}" if self.language.get() == "English" else f"已添加格式：{format_name}\n\n格式类型：按角色列出作者\n模板：{template}"))
                add_window.destroy()
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text=("Detect grouping" if self.language.get() == "English" else "识别格式"), command=lambda: detect_from_example()).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=("Save template" if self.language.get() == "English" else "保存格式"), command=save_format).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=("Cancel" if self.language.get() == "English" else "取消"), command=add_window.destroy).pack(side=tk.LEFT, padx=5)
        
        def detect_from_example():
            """从示例识别格式"""
            text = text_widget.get('1.0', tk.END).strip()
            if not text:
                result_label.config(text=("Paste an example statement first" if self.language.get() == "English" else "请先粘贴示例文本"), foreground='red')
                return
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                result_label.config(text=("No valid content found" if self.language.get() == "English" else "未找到有效内容"), foreground='red')
                return
            
            # 检测是否是按作者格式
            is_author_based = False
            for line in lines[:3]:
                if ':' in line:
                    before_colon = line.split(':')[0].strip()
                    # 检查是否是缩写格式（如 C.W. 或 C.W）
                    if ('.' in before_colon) or (len(before_colon) <= 5 and before_colon.isupper()):
                        is_author_based = True
                        break
            
            if is_author_based:
                format_type.set("author")
                result_label.config(text=("Suggested grouping: by author\nExample: Z.S.: Conceptualization, Methodology." if self.language.get() == "English" else "✓ 检测为：按作者列出角色格式\n示例：Z.S.: Conceptualization, Methodology."), foreground='green')
            else:
                format_type.set("role")
                result_label.config(text=("Suggested grouping: by role\nExample: Zhang San and Li Si: Conceptualization." if self.language.get() == "English" else "✓ 检测为：按角色列出作者格式\n示例：Zhang San and Li Si: Conceptualization."), foreground='green')
    
    def save_custom_formats(self):
        """保存自定义格式到文件"""
        custom_file = os.path.join(os.path.dirname(__file__), "custom_formats.json")
        try:
            with open(custom_file, 'w', encoding='utf-8') as f:
                json.dump(JOURNAL_FORMATS, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def delete_format(self):
        """删除自定义格式"""
        current_format = self.format_var.get()
        
        # 系统预设格式不能删除
        system_formats = ['Elsevier', 'Springer', 'Wiley', 'Nature', 'Science', 'npj Digital Medicine', 'Custom']
        
        if current_format in system_formats:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Built-in templates cannot be deleted' if self.language.get() == "English" else '系统预设格式不能删除'))
            return
        
        if messagebox.askyesno(('Confirm' if self.language.get() == "English" else '确认'), f"确定删除格式：{current_format}？"):
            if current_format in JOURNAL_FORMATS:
                del JOURNAL_FORMATS[current_format]
                
                # 更新下拉框
                if self.format_combo:
                    self.format_combo['values'] = list(JOURNAL_FORMATS.keys())
                    self.format_var.set('Elsevier')
                
                # 保存到文件
                self.save_custom_formats()
                
                messagebox.showinfo(('Success' if self.language.get() == "English" else '成功'), f"已删除格式：{current_format}")
    
    def load_custom_formats(self):
        """从文件加载自定义格式"""
        custom_file = os.path.join(os.path.dirname(__file__), "custom_formats.json")
        if os.path.exists(custom_file):
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    custom_formats = json.load(f)
                    JOURNAL_FORMATS.update(custom_formats)
            except:
                pass
    
    def copy_to_clipboard(self):
        text = self.output_text.get('1.0', tk.END).strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo(('Success' if self.language.get() == "English" else '成功'), ('Copied to clipboard' if self.language.get() == "English" else '已复制到剪贴板'))
        
    def save_data(self):
        """保存所有配置（作者信息和角色分配）到JSON文件，方便下次使用"""
        data = {
            'authors': self.authors,
            'author_order': self.author_order,
            'roles': {role: {abbr: var.get() for abbr, var in authors.items()} 
                     for role, authors in self.role_vars.items()}
        }
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="author_contributions.json"
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo(('Success' if self.language.get() == "English" else '成功'), f"配置已保存到:\n{filename}\n\n保存的内容包括：\n- 作者列表和顺序\n- 每位作者的角色分配勾选")
            
    def load_data(self):
        """从JSON文件加载之前保存的配置（作者信息和角色分配）"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title=('Load project' if self.language.get() == "English" else '加载配置文件')
        )
        
        if not filename:
            return
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                raise ValueError("配置必须是 JSON 对象")
            authors = data.get('authors', {})
            if not isinstance(authors, dict):
                raise ValueError("作者列表格式错误")
            authors = {k: {'full': v, 'abbr': ''} if isinstance(v, str) else v for k, v in authors.items()}
            for name, value in authors.items():
                if not isinstance(name, str) or not name.strip() or not isinstance(value, dict) or not isinstance(value.get('full'), str) or not value['full'].strip():
                    raise ValueError("作者信息不完整")
            order = data.get('author_order', list(authors))
            if not isinstance(order, list) or any(not isinstance(x, str) for x in order) or len(order) != len(set(order)) or set(order) != set(authors):
                raise ValueError("作者顺序与作者列表不一致")
            roles = data.get('roles', {})
            if not isinstance(roles, dict) or any(not isinstance(v, dict) or any(type(x) is not bool for x in v.values()) for v in roles.values()):
                raise ValueError("角色勾选必须为 true 或 false")
            self.role_vars.clear()
            self.authors = authors
            self.author_order = data.get('author_order', list(self.authors.keys()))
            self.update_author_list()
            self.update_table()
            
            # 恢复复选框状态
            roles = data.get('roles', {})
            for role, authors in roles.items():
                if role in self.role_vars:
                    for abbr, checked in authors.items():
                        if abbr in self.role_vars[role]:
                            self.role_vars[role][abbr].set(checked)
                            # 更新显示
                            for i, (role_abbr, _) in enumerate(CREDIT_ROLES):
                                if role_abbr == role:
                                    item = self.tree.get_children()[i]
                                    col_index = self.author_order.index(abbr) + 2
                                    self.tree.set(item, f"#{col_index}", "☑" if checked else "☐")
                                    break
                                    
            messagebox.showinfo(('Success' if self.language.get() == "English" else '成功'), f"配置已加载！\n\n加载的内容包括：\n- {len(self.authors)} 位作者\n- 之前的角色分配勾选状态")
        except Exception as e:
            messagebox.showerror(('Error' if self.language.get() == "English" else '错误'), f"加载失败: {str(e)}")
            
    def export_word(self):
        text = self.output_text.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning(('Warning' if self.language.get() == "English" else '警告'), ('Generate a statement first' if self.language.get() == "English" else '请先生成贡献声明'))
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="Authors_Contributions.txt"
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Authors' Contributions\n\n")
                f.write(text)
            messagebox.showinfo(('Success' if self.language.get() == "English" else '成功'), f"已导出到:\n{filename}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AuthorContributionsApp(root)
    root.mainloop()
