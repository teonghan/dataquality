# 🧼 Data Quality & Cleaning Assistant

*Because messy data deserves some TLC!*

Try it live 👉 [dataqualityutm.streamlit.app](https://dataqualityutm.streamlit.app)

---

## 🔍 Overview

**Data Quality & Cleaning Assistant** is a user-friendly Streamlit app that helps you **analyze**, **clean**, and **understand** your data — all without writing a single line of code.

Whether you're a data pro or an Excel warrior, this app:
- 🕵️ Detects common data issues like missing values, duplicates, messy text, and more
- ✨ Offers **one-click auto-cleaning**
- 📊 Gives **cleaning tips** (with Excel & Google Sheets formulas)
- 📥 Lets you **download cleaned data** with ease

You can upload `.csv`, `.tsv`, `.xlsx`, or even structured `.pdf` files with tables.

---

## 🧰 Key Features

- 📂 **File upload support**: CSV, Excel (.xlsx/.xls), TSV, and PDFs with tables
- 🧠 **Automatic issue detection**:
  - Missing values
  - Duplicate rows
  - Inconsistent categories (e.g. casing, extra spaces)
  - Incorrect data types (numbers stored as text)
  - Outliers (via IQR)
  - Messy date formats
  - Non-unique IDs
- ⚡ **Auto-clean** with one click:
  - Trims whitespace
  - Standardizes casing
  - Converts datatypes
  - Fills missing values
  - Removes duplicates
- 💡 **Cleaning suggestions** for Excel & Google Sheets users
- 📊 Column-level stats & summaries
- 📥 Cleaned file download (.csv)

---

## 🚀 Try it Online

Use it instantly via Streamlit Cloud:  
👉 [https://dataqualityutm.streamlit.app](https://dataqualityutm.streamlit.app)

---

## 🛠 Installation

### Option 1: Quick install (macOS only)

Run the automated macOS installer:

```bash
bash installer-macos-universal.sh
```

This will:
- Detect your Mac architecture (Intel or ARM)
- Install Miniforge and dependencies
- Create a launchable `.app` on your desktop

---

### Option 2: One-Click Windows Installer

Just run the bundled installer script:

```powershell
Right-click → Run with PowerShell → installer-windows.ps1
```

This will:
- Detect your Anaconda or Miniconda installation
- Create (or update) the `dataquality` environment from `__environment__.yml`
- Create a desktop shortcut (`Start Data Quality App`) to launch the app
- Automatically generate a launcher (`start-streamlit-app.ps1`)
- Generate a clean uninstaller (`uninstall-streamlit-app.ps1`)

After installation, just double-click the desktop shortcut to start your app!

> 💡 **Note**: You must have Anaconda or Miniconda installed first.  
> If not found, the installer will show a message and stop.

---

### Option 3: Manual setup (Windows/Linux/macOS)

1. Clone the repository:

```bash
git clone https://github.com/teonghan/dataquality.git
cd dataquality
```

2. (Recommended) Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

> If you're extracting tables from PDFs, make sure to also:
> - Install [Ghostscript](https://www.ghostscript.com/) (required by `camelot-py`)
> - Optionally, test PDF support separately before using Camelot

4. Run the app:

```bash
streamlit run app.py
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙌 Acknowledgements

Built with ❤️ using:
- [Streamlit](https://streamlit.io/)
- [pandas](https://pandas.pydata.org/)
- [Camelot](https://camelot-py.readthedocs.io/en/master/) for PDF table extraction
- [PyPDF2](https://pypi.org/project/PyPDF2/)

---

Let your data breathe. Clean it up today ✨  
[→ Try the App](https://dataqualityutm.streamlit.app)
