# Folder Comparator GUI

A PyQt6-based GUI tool for comparing contents between two folders, with file classification and report generation capabilities.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20MacOS-lightgrey)

## ✨ Features

- 🖥️ **Modern GUI Interface** - User-friendly interface built with PyQt6
- 🔍 **Visual Comparison** - Color-coded results for easy identification
- 📊 **Detailed File Information** - Shows file names, paths, and sizes
- 📁 **Automatic File Classification** - Organizes files into three categories:
  - Files unique to Folder 1 (Green)
  - Files unique to Folder 2 (Blue)
  - Common files in both folders (Gray)
- 📄 **Report Generation** - Creates detailed comparison reports in TXT format
- 🗂️ **File Organization** - Optionally copies files to categorized folders
- ⚡ **Multithreading** - Fast processing with progress indication

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- PyQt6 library

### Install Dependencies
```bash
pip install PyQt6
```

## 📖 Usage

1. **Run the script:**
   ```bash
   python Folder-Comparator-GUI.py
   ```

2. **Select folders:**
   - Enter paths manually or use the browse buttons
   - Drag and drop folders directly into the input fields

3. **Configure options:**
   - Choose whether to save reports
   - Select whether to classify and copy files

4. **Start comparison:**
   - Click "Start Comparison"
   - View real-time progress and results

5. **Review results:**
   - Files are displayed in three color-coded tables
   - Open file locations with one click
   - Access generated reports and organized files

## 🖼️ Screenshots

*(Add screenshots of your application here)*

## 🛠️ Technical Details

### File Structure
```
Folder-Comparator-GUI/
├── Folder-Comparator-GUI.py   # Main application
├── README.md                  # This file
├── requirements.txt           # Dependencies
└── LICENSE                    # MIT License
```

### Key Functions
- **Drag-and-drop support** for easy folder selection
- **Real-time progress tracking** with multithreading
- **Color-coded UI** for intuitive results display
- **Cross-platform compatibility** (Windows, Linux, macOS)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 👤 Author

**你的名字**
- GitHub: [@你的用户名](https://github.com/你的用户名)
- Email: 你的邮箱@example.com

## 🙏 Acknowledgments

- Thanks to the PyQt6 team for the excellent GUI framework
- Inspired by various folder comparison tools