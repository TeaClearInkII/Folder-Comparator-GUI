import os
import sys
import shutil
import hashlib
from pathlib import Path
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QFileDialog, QHeaderView, QAbstractItemView, 
                             QFrame, QGroupBox, QSplitter, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QColor, QFont

# ----------------------
# Worker线程
# ----------------------
class FolderCompareThread(QThread):
    update_progress = pyqtSignal(int, int, str)
    log_signal = pyqtSignal(str, str)
    file_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, folder1, folder2, save_report=False, classify_files=False, max_threads=10):
        super().__init__()
        self.folder1 = folder1
        self.folder2 = folder2
        self.save_report = save_report
        self.classify_files = classify_files
        self.max_threads = max_threads
        self.output_dir = None
        
    def run(self):
        try:
            # 获取程序所在目录（兼容 PyInstaller 打包）
            if getattr(sys, 'frozen', False):
                script_dir = os.path.dirname(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 获取文件夹1中的文件列表
            self.log_signal.emit(f"正在扫描文件夹1: {self.folder1}", "blue")
            try:
                files1 = {f.name: f for f in Path(self.folder1).iterdir() if f.is_file()}
            except Exception as e:
                self.log_signal.emit(f"❌ 无法访问文件夹1: {e}", "red")
                return
            
            # 获取文件夹2中的文件列表
            self.log_signal.emit(f"正在扫描文件夹2: {self.folder2}", "blue")
            try:
                files2 = {f.name: f for f in Path(self.folder2).iterdir() if f.is_file()}
            except Exception as e:
                self.log_signal.emit(f"❌ 无法访问文件夹2: {e}", "red")
                return
            
            # 计算文件差异
            self.log_signal.emit("正在比较文件...", "blue")
            common_files = sorted(files1.keys() & files2.keys())
            unique_in_folder1 = sorted(files1.keys() - files2.keys())
            unique_in_folder2 = sorted(files2.keys() - files1.keys())
            
            # 发送文件信息到主界面
            total_files = len(common_files) + len(unique_in_folder1) + len(unique_in_folder2)
            processed = 0
            
            # 预先计算输出目录（如果勾选了保存报告或分类复制）
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = None
            if self.save_report or self.classify_files:
                output_dir = os.path.join(script_dir, f"文件夹比较分析_{timestamp}")
            
            # 预先创建分类子目录
            category_dirs = {
                "folder1_unique": "文件夹1独有的文件",
                "folder2_unique": "文件夹2独有的文件",
                "common": "共有的文件",
            }
            if self.classify_files and output_dir:
                for dir_name in category_dirs.values():
                    os.makedirs(os.path.join(output_dir, dir_name), exist_ok=True)
            
            # 发送文件夹1独有的文件
            for filename in unique_in_folder1:
                processed += 1
                self.update_progress.emit(processed, total_files, "正在处理文件夹1独有文件...")
                src = str(files1[filename])
                if self.classify_files and output_dir:
                    try:
                        shutil.copy2(src, os.path.join(output_dir, category_dirs["folder1_unique"], filename))
                    except Exception as e:
                        self.log_signal.emit(f"⚠ 复制失败 {filename}: {e}", "orange")
                self.file_signal.emit({
                    "filename": filename,
                    "category": "folder1_unique",
                    "path": src,
                    "size": os.path.getsize(src) if os.path.exists(src) else 0,
                    "output_dir": output_dir,
                    "classify_files": self.classify_files
                })
            
            # 发送文件夹2独有的文件
            for filename in unique_in_folder2:
                processed += 1
                self.update_progress.emit(processed, total_files, "正在处理文件夹2独有文件...")
                src = str(files2[filename])
                if self.classify_files and output_dir:
                    try:
                        shutil.copy2(src, os.path.join(output_dir, category_dirs["folder2_unique"], filename))
                    except Exception as e:
                        self.log_signal.emit(f"⚠ 复制失败 {filename}: {e}", "orange")
                self.file_signal.emit({
                    "filename": filename,
                    "category": "folder2_unique",
                    "path": src,
                    "size": os.path.getsize(src) if os.path.exists(src) else 0,
                    "output_dir": output_dir,
                    "classify_files": self.classify_files
                })
            
            # 发送共有文件（并发哈希比较 + 复制）
            if common_files:
                with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                    future_to_file = {}
                    for filename in common_files:
                        path1 = str(files1[filename])
                        path2 = str(files2[filename])
                        size1 = os.path.getsize(path1) if os.path.exists(path1) else 0
                        size2 = os.path.getsize(path2) if os.path.exists(path2) else 0
                        future = executor.submit(
                            self.process_common_file,
                            path1, path2, output_dir,
                            category_dirs["common"], filename
                        )
                        future_to_file[future] = {
                            "filename": filename,
                            "path1": path1,
                            "path2": path2,
                            "size1": size1,
                            "size2": size2,
                        }
                    
                    for future in as_completed(future_to_file):
                        processed += 1
                        self.update_progress.emit(processed, total_files, "正在比较共有文件内容...")
                        info = future_to_file[future]
                        hash_match = future.result()
                        self.file_signal.emit({
                            "filename": info["filename"],
                            "category": "common",
                            "path1": info["path1"],
                            "path2": info["path2"],
                            "size1": info["size1"],
                            "size2": info["size2"],
                            "hash_match": hash_match,
                            "output_dir": output_dir,
                            "classify_files": self.classify_files
                        })
            
            # 创建输出目录（如果需要）
            result = {
                "folder1": self.folder1,
                "folder2": self.folder2,
                "common_files": common_files,
                "unique_in_folder1": unique_in_folder1,
                "unique_in_folder2": unique_in_folder2,
                "files1": files1,
                "files2": files2,
                "output_dir": None
            }
            
            self.output_dir = output_dir
            result["output_dir"] = output_dir
            
            if self.save_report or self.classify_files:
                
                try:
                    os.makedirs(self.output_dir, exist_ok=True)
                    
                    # 保存报告
                    if self.save_report:
                        report_path = os.path.join(self.output_dir, f"文件夹比较报告_{timestamp}.txt")
                        self.save_report_to_file(result, report_path)
                        self.log_signal.emit(f"✅ 报告已保存: {report_path}", "green")
                    
                    if self.classify_files:
                        self.log_signal.emit(f"✅ 文件分类复制完成!", "green")
                        
                except Exception as e:
                    self.log_signal.emit(f"❌ 创建输出目录失败: {e}", "red")
            
            self.log_signal.emit(f"✅ 比较完成! 共处理 {total_files} 个文件", "green")
            self.finished_signal.emit(result)
            
        except Exception as e:
            self.log_signal.emit(f"❌ 比较过程中出现错误: {e}", "red")
    
    def save_report_to_file(self, result, report_path):
        """保存报告到文件"""
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("文件夹比较结果报告\n")
                f.write("=" * 60 + "\n")
                f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"文件夹1: {result['folder1']}\n")
                f.write(f"文件夹2: {result['folder2']}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write("只在文件夹1中的文件:\n")
                if result['unique_in_folder1']:
                    for file in result['unique_in_folder1']:
                        f.write(f"  {file}\n")
                else:
                    f.write("  (无)\n")
                
                f.write("\n只在文件夹2中的文件:\n")
                if result['unique_in_folder2']:
                    for file in result['unique_in_folder2']:
                        f.write(f"  {file}\n")
                else:
                    f.write("  (无)\n")
                
                f.write("\n两个文件夹都有的文件:\n")
                if result['common_files']:
                    for file in result['common_files']:
                        f.write(f"  {file}\n")
                else:
                    f.write("  (无)\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write("统计:\n")
                f.write(f"文件夹1中的文件总数: {len(result['unique_in_folder1']) + len(result['common_files'])}\n")
                f.write(f"文件夹2中的文件总数: {len(result['unique_in_folder2']) + len(result['common_files'])}\n")
                f.write(f"共同文件数: {len(result['common_files'])}\n")
                f.write(f"差异文件数: {len(result['unique_in_folder1']) + len(result['unique_in_folder2'])}\n")
                
            return True
        except Exception as e:
            self.log_signal.emit(f"❌ 保存报告失败: {e}", "red")
            return False
    
    def compare_file_hash(self, path1, path2):
        """比较两个文件的 MD5 哈希值"""
        try:
            hash1 = hashlib.md5()
            hash2 = hashlib.md5()
            with open(path1, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hash1.update(chunk)
            with open(path2, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hash2.update(chunk)
            return hash1.digest() == hash2.digest()
        except Exception as e:
            self.log_signal.emit(f"⚠ 无法比较文件哈希 {os.path.basename(path1)}: {e}", "orange")
            return None
    
    def process_common_file(self, path1, path2, output_dir, category_dir, filename):
        """处理共有文件：复制到输出目录 + 哈希比较"""
        if output_dir and self.classify_files:
            dst = os.path.join(output_dir, category_dir, filename)
            try:
                shutil.copy2(path1, dst)
            except Exception as e:
                self.log_signal.emit(f"⚠ 复制失败 {filename}: {e}", "orange")
        return self.compare_file_hash(path1, path2)

# ----------------------
# GUI界面
# ----------------------
class FolderCompareGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件夹内容比较工具 v3.0")
        self.resize(1200, 800)
        self.setAcceptDrops(True)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # -------------------
        # 控制面板区域
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        control_layout = QVBoxLayout(control_frame)
        
        # 标题
        title_label = QLabel("文件夹内容比较与分类工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1565C0; padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        control_layout.addWidget(title_label)
        
        # 功能说明
        desc_label = QLabel("功能说明: 比较两个文件夹中的文件名称，相同文件用灰色显示，不同文件用绿色显示。结果按文件名称排序，可选择保存分析报告和分类复制文件。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; padding: 5px; background-color: #f8f8f8; border: 1px solid #ddd; border-radius: 3px;")
        control_layout.addWidget(desc_label)
        
        # 文件夹1输入
        folder1_layout = QHBoxLayout()
        folder1_layout.addWidget(QLabel("文件夹1路径:"))
        self.folder1_edit = QLineEdit()
        self.folder1_edit.setPlaceholderText("可拖入文件夹或手动输入路径，或点击浏览选择")
        folder1_layout.addWidget(self.folder1_edit, 4)
        self.browse_btn1 = QPushButton("浏览")
        self.browse_btn1.clicked.connect(lambda: self.browse_folder(1))
        folder1_layout.addWidget(self.browse_btn1, 1)
        control_layout.addLayout(folder1_layout)
        
        # 文件夹2输入
        folder2_layout = QHBoxLayout()
        folder2_layout.addWidget(QLabel("文件夹2路径:"))
        self.folder2_edit = QLineEdit()
        self.folder2_edit.setPlaceholderText("可拖入文件夹或手动输入路径，或点击浏览选择")
        folder2_layout.addWidget(self.folder2_edit, 4)
        self.browse_btn2 = QPushButton("浏览")
        self.browse_btn2.clicked.connect(lambda: self.browse_folder(2))
        folder2_layout.addWidget(self.browse_btn2, 1)
        control_layout.addLayout(folder2_layout)
        
        # 选项
        options_layout = QHBoxLayout()
        self.save_report_cb = QCheckBox("保存分析报告")
        self.save_report_cb.setChecked(True)
        self.classify_files_cb = QCheckBox("分类复制文件")
        self.classify_files_cb.setChecked(True)
        options_layout.addWidget(self.save_report_cb)
        options_layout.addWidget(self.classify_files_cb)
        options_layout.addStretch()
        control_layout.addLayout(options_layout)
        
        # 按钮和进度条
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始比较")
        self.start_btn.clicked.connect(self.start_comparison)
        button_layout.addWidget(self.start_btn)
        
        self.open_dir_btn = QPushButton("打开生成目录")
        self.open_dir_btn.clicked.connect(self.open_output_dir)
        self.open_dir_btn.setEnabled(False)
        button_layout.addWidget(self.open_dir_btn)
        
        self.open_history_btn = QPushButton("打开分析目录")
        self.open_history_btn.clicked.connect(self.open_analysis_dir)
        button_layout.addWidget(self.open_history_btn)
        
        button_layout.addStretch()
        
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(300)
        button_layout.addWidget(self.progress)
        
        self.status_label = QLabel("就绪")
        self.status_label.setMaximumWidth(200)
        button_layout.addWidget(self.status_label)
        
        control_layout.addLayout(button_layout)
        
        # 日志框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 10pt;")
        control_layout.addWidget(self.log_text)
        
        main_layout.addWidget(control_frame)
        
        # -------------------
        # 表格区域 - 使用QSplitter分割三个区域
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 创建三个分类的表格
        self.tables = {}
        categories = [
            ("folder1_unique", "文件夹1独有的文件", "#4CAF50", "只在第一个文件夹中存在的文件"),
            ("folder2_unique", "文件夹2独有的文件", "#2196F3", "只在第二个文件夹中存在的文件"),
            ("common", "共有的文件", "#9E9E9E", "两个文件夹中都存在的文件")
        ]
        
        for cat_id, cat_name, color, description in categories:
            # 创建分组框
            group_box = QGroupBox(cat_name)
            group_box.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {color}; font-size: 14px; }}")
            
            # 创建布局
            group_layout = QVBoxLayout()
            
            # 添加描述标签
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"color: {color}; font-size: 12px; padding-bottom: 5px;")
            group_layout.addWidget(desc_label)
            
            # 创建表格
            table = QTableWidget()
            table.setColumnCount(3)  # 文件名、大小、操作
            table.setHorizontalHeaderLabels(["文件名", "大小", "操作"])
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 文件名列自适应
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 大小列
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 操作列
            table.setSortingEnabled(True)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setAlternatingRowColors(True)
            
            # 根据分类设置行颜色
            if cat_id == "folder1_unique":
                table.setStyleSheet("QTableWidget::item { color: #4CAF50; }")
            elif cat_id == "folder2_unique":
                table.setStyleSheet("QTableWidget::item { color: #2196F3; }")
            else:
                table.setStyleSheet("QTableWidget::item { color: #757575; }")
            
            group_layout.addWidget(table)
            group_box.setLayout(group_layout)
            
            self.splitter.addWidget(group_box)
            self.tables[cat_id] = table
        
        # 设置分割器各部分的初始大小
        self.splitter.setSizes([300, 300, 300])
        main_layout.addWidget(self.splitter, 1)
        
        self.setLayout(main_layout)
        # 获取程序所在目录（兼容 PyInstaller 打包）
        if getattr(sys, 'frozen', False):
            self.script_dir = os.path.dirname(sys.executable)
        else:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = None
        self.result_data = None
    
    # 拖拽支持
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            # 获取拖拽的路径
            path = urls[0].toLocalFile()
            
            # 检查焦点在哪个输入框
            if self.folder1_edit.hasFocus():
                self.folder1_edit.setText(path)
            elif self.folder2_edit.hasFocus():
                self.folder2_edit.setText(path)
            else:
                # 如果没有焦点，则交替设置到两个输入框
                if not self.folder1_edit.text():
                    self.folder1_edit.setText(path)
                elif not self.folder2_edit.text():
                    self.folder2_edit.setText(path)
                else:
                    # 两个都有内容，询问用户
                    self.folder1_edit.setText(path)
                    self.folder2_edit.clear()
    
    def browse_folder(self, folder_num):
        folder = QFileDialog.getExistingDirectory(self, f"选择文件夹{folder_num}")
        if folder:
            if folder_num == 1:
                self.folder1_edit.setText(folder)
            else:
                self.folder2_edit.setText(folder)
    
    def start_comparison(self):
        folder1 = self.folder1_edit.text().strip()
        folder2 = self.folder2_edit.text().strip()
        
        if not folder1 or not folder2:
            self.log_text.append("❌ 请先选择两个文件夹")
            return
        
        folder1 = folder1.strip('"\'')
        folder2 = folder2.strip('"\'')
        
        if not os.path.exists(folder1):
            self.log_text.append(f"❌ 文件夹1不存在: {folder1}")
            return
        
        if not os.path.exists(folder2):
            self.log_text.append(f"❌ 文件夹2不存在: {folder2}")
            return
        
        # 清空所有表格
        for table in self.tables.values():
            table.setRowCount(0)
        
        self.progress.setValue(0)
        self.output_dir = None
        self.open_dir_btn.setEnabled(False)
        self.log_text.clear()
        
        self.worker = FolderCompareThread(
            folder1,
            folder2,
            self.save_report_cb.isChecked(),
            self.classify_files_cb.isChecked()
        )
        self.worker.update_progress.connect(self.on_progress)
        self.worker.log_signal.connect(self.on_log)
        self.worker.file_signal.connect(self.on_file)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()
    
    def on_progress(self, current, total, status):
        self.status_label.setText(status)
        if total > 0:
            percent = int(current / total * 100)
            self.progress.setFormat(f"[{current}/{total}] {percent}%")
            self.progress.setValue(percent)
    
    def on_log(self, msg, color):
        if color == "red":
            self.log_text.setTextColor(QColor(255, 0, 0))
        elif color == "green":
            self.log_text.setTextColor(QColor(0, 128, 0))
        elif color == "orange":
            self.log_text.setTextColor(QColor(255, 140, 0))
        elif color == "blue":
            self.log_text.setTextColor(QColor(0, 0, 255))
        else:
            self.log_text.setTextColor(QColor(0, 0, 0))
        
        self.log_text.append(msg)
        self.log_text.moveCursor(self.log_text.textCursor().MoveOperation.End)
    
    def on_file(self, file_info):
        category = file_info["category"]
        table = self.tables.get(category)
        if not table:
            return
        
        row = table.rowCount()
        table.insertRow(row)
        
        # 文件名
        filename_item = QTableWidgetItem(file_info["filename"])
        
        # 根据分类设置颜色
        if category == "folder1_unique":
            filename_item.setForeground(QColor("#4CAF50"))  # 绿色
        elif category == "folder2_unique":
            filename_item.setForeground(QColor("#2196F3"))  # 蓝色
        else:
            filename_item.setForeground(QColor("#757575"))  # 灰色
        
        table.setItem(row, 0, filename_item)
        
        # 大小
        if category == "common":
            size1 = file_info.get("size1", 0)
            size2 = file_info.get("size2", 0)
            hash_match = file_info.get("hash_match")
            
            if size1 == size2 and hash_match is True:
                display = f"✅ 完全相同\n{self.format_size(size1)}"
            elif size1 == size2 and hash_match is False:
                display = f"🔴 内容不同\n{self.format_size(size1)}"
            elif size1 != size2:
                display = f"⚠ 大小不同\n文件夹1: {self.format_size(size1)}\n文件夹2: {self.format_size(size2)}"
            else:
                display = f"文件夹1: {self.format_size(size1)}\n文件夹2: {self.format_size(size2)}"
            
            size_item = QTableWidgetItem(display)
            if size1 == size2 and hash_match is True:
                size_item.setForeground(QColor(0, 128, 0))
            elif hash_match is False or size1 != size2:
                size_item.setForeground(QColor(255, 0, 0))
        else:
            size = file_info.get("size", 0)
            size_item = QTableWidgetItem(self.format_size(size))
        
        table.setItem(row, 1, size_item)
        
        # 操作按钮
        classify_files = file_info.get("classify_files", False)
        output_dir = file_info.get("output_dir")
        
        category_dir_map = {
            "folder1_unique": "文件夹1独有的文件",
            "folder2_unique": "文件夹2独有的文件",
            "common": "共有的文件",
        }
        
        if category == "common":
            path1 = file_info.get("path1", "")
            path2 = file_info.get("path2", "")
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            if path1 and os.path.exists(path1):
                btn1 = QPushButton("文件夹1")
                btn1.setToolTip("打开文件夹1中的文件位置")
                btn1.clicked.connect(lambda checked, p=os.path.dirname(path1): self.open_file_location(p))
                btn_layout.addWidget(btn1)
            if path2 and os.path.exists(path2):
                btn2 = QPushButton("文件夹2")
                btn2.setToolTip("打开文件夹2中的文件位置")
                btn2.clicked.connect(lambda checked, p=os.path.dirname(path2): self.open_file_location(p))
                btn_layout.addWidget(btn2)
            # 打开复制路径按钮
            if classify_files and output_dir:
                copied_path = os.path.join(output_dir, category_dir_map[category], file_info["filename"])
                if os.path.exists(copied_path):
                    copy_btn = QPushButton("复制件")
                    copy_btn.setToolTip("打开分类复制后的文件位置")
                    copy_btn.clicked.connect(lambda checked, p=os.path.dirname(copied_path): self.open_file_location(p))
                    btn_layout.addWidget(copy_btn)
            btn_layout.addStretch()
            table.setCellWidget(row, 2, btn_widget)
        else:
            path = file_info.get("path", "")
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            if path and os.path.exists(path):
                open_btn = QPushButton("打开位置")
                open_btn.clicked.connect(lambda checked, p=os.path.dirname(path): self.open_file_location(p))
                open_btn.setMaximumWidth(80)
                btn_layout.addWidget(open_btn)
            # 打开复制路径按钮
            if classify_files and output_dir:
                copied_path = os.path.join(output_dir, category_dir_map[category], file_info["filename"])
                if os.path.exists(copied_path):
                    copy_btn = QPushButton("复制件")
                    copy_btn.setToolTip("打开分类复制后的文件位置")
                    copy_btn.clicked.connect(lambda checked, p=os.path.dirname(copied_path): self.open_file_location(p))
                    btn_layout.addWidget(copy_btn)
            btn_layout.addStretch()
            table.setCellWidget(row, 2, btn_widget)
    
    def on_finished(self, result):
        self.result_data = result
        self.output_dir = result.get("output_dir")
        
        if self.output_dir:
            self.open_dir_btn.setEnabled(True)
        
        # 显示统计信息
        total1 = len(result["unique_in_folder1"]) + len(result["common_files"])
        total2 = len(result["unique_in_folder2"]) + len(result["common_files"])
        common_count = len(result["common_files"])
        diff_count = len(result["unique_in_folder1"]) + len(result["unique_in_folder2"])
        
        stats_text = f"✅ 比较完成! 统计: 文件夹1有 {total1} 个文件, 文件夹2有 {total2} 个文件, 共同文件 {common_count} 个, 差异文件 {diff_count} 个"
        self.log_text.append(stats_text)
        
        # 更新进度条
        self.progress.setValue(100)
        self.status_label.setText("完成")
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
    
    def open_file_location(self, path):
        """打开文件所在位置"""
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.log_text.append(f"❌ 路径不存在: {path}")
    
    def open_output_dir(self):
        """打开输出目录"""
        if self.output_dir and os.path.exists(self.output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir))
        elif self.result_data and self.result_data.get("output_dir"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.result_data['output_dir']))
        else:
            self.log_text.append("❌ 输出目录不存在")
    
    def open_analysis_dir(self):
        """打开历史分析目录（脚本所在目录，所有分析结果存放于此）"""
        if self.script_dir and os.path.exists(self.script_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.script_dir))
            self.log_text.append(f"📂 已打开分析目录: {self.script_dir}")
        else:
            self.log_text.append("❌ 无法定位分析目录")

# ----------------------
# 启动
# ----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = FolderCompareGUI()
    gui.show()
    sys.exit(app.exec())