import streamlit as st
import pandas as pd
import io
import PyPDF2 # Used for basic PDF text extraction
# Import camelot for PDF table extraction. Requires Ghostscript to be installed.
try:
    import camelot
except ImportError:
    st.error("Camelot library not found. Please install it using: pip install 'camelot-py[cv]'")
    st.error("Also, ensure Ghostscript is installed and in your system's PATH. See https://camelot-py.readthedocs.io/en/master/user/install-deps.html for details.")
    camelot = None


# --- Configuration and Setup ---
st.set_page_config(
    page_title="Data Quality & Cleaning Assistant",
    layout="wide",
    initial_sidebar_state="expanded" # Makes the sidebar permanent
)

# --- Helper Functions for Data Loading ---

def load_csv_tsv(uploaded_file, delimiter=','):
    """
    Loads a CSV or TSV file into a Pandas DataFrame.
    Handles potential decoding errors.
    """
    try:
        # Attempt to read with specified delimiter
        df = pd.read_csv(uploaded_file, delimiter=delimiter)
        return df
    except UnicodeDecodeError:
        # If decode error, try reading with 'latin1' encoding
        uploaded_file.seek(0) # Reset file pointer
        df = pd.read_csv(uploaded_file, delimiter=delimiter, encoding='latin1')
        return df
    except Exception as e:
        st.error(f"Error loading CSV/TSV: {e}")
        return None

def load_excel(uploaded_file):
    """
    Loads an Excel file (XLSX or XLS) into a Pandas DataFrame.
    Asks user to select sheet if multiple sheets are present.
    """
    try:
        # Read all sheets to check for multiple sheets
        xls = pd.ExcelFile(uploaded_file)
        if len(xls.sheet_names) > 1:
            selected_sheet = st.sidebar.selectbox(
                "Select sheet to load:", xls.sheet_names
            )
            df = pd.read_excel(xls, sheet_name=selected_sheet)
        else:
            df = pd.read_excel(xls)
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None

def extract_from_pdf(uploaded_file, attempt_table_extraction=False):
    """
    Attempts to extract tables from PDF using Camelot if requested,
    falls back to text extraction if no tables are found or Camelot is not available/requested.
    Returns a dictionary with 'type' ('dataframe' or 'text') and 'content'.
    """
    if attempt_table_extraction and camelot:
        try:
            # Camelot expects a file path, so we need to save the uploaded file temporarily
            # or pass it as a BytesIO object if camelot supports it (it prefers paths).
            # Camelot's read_pdf can take a file-like object directly.
            tables = camelot.read_pdf(uploaded_file, pages='all', flavor='lattice', # 'lattice' for line-separated tables, 'stream' for whitespace-separated
                                      line_scale=40) # Adjust line_scale for better detection

            if tables.n > 0:
                st.success(f"✅ Found {tables.n} table(s) in the PDF using Camelot.")
                # For simplicity, we'll return the first table found as a DataFrame
                # You could extend this to allow selection of multiple tables.
                return {'type': 'dataframe', 'content': tables[0].df}
            else:
                st.info("No tables found using Camelot. Attempting basic text extraction.")
                text_content = extract_text_from_pdf_basic(uploaded_file)
                if text_content:
                    return {'type': 'text', 'content': text_content}
                else:
                    return {'type': 'none', 'content': None}
        except Exception as e:
            st.warning(f"Could not extract tables from PDF using Camelot (Error: {e}). Falling back to basic text extraction.")
            text_content = extract_text_from_pdf_basic(uploaded_file)
            if text_content:
                return {'type': 'text', 'content': text_content}
            else:
                return {'type': 'none', 'content': None}
    else:
        if attempt_table_extraction and not camelot:
             st.warning("Camelot is not installed or configured. Cannot attempt table extraction. Falling back to basic PDF text extraction.")

        text_content = extract_text_from_pdf_basic(uploaded_file)
        if text_content:
            return {'type': 'text', 'content': text_content}
        else:
            return {'type': 'none', 'content': None}

def extract_text_from_pdf_basic(uploaded_file):
    """
    Extracts text content from a PDF file using PyPDF2.
    This is a fallback for when Camelot doesn't find tables or is not available.
    """
    try:
        # Reset file pointer for PyPDF2 after Camelot might have read it
        uploaded_file.seek(0)
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF with PyPDF2: {e}.")
        return None

# --- Data Upload Function (Sidebar) ---

def data_upload_sidebar():
    """
    Handles single file upload in the Streamlit sidebar.
    Returns a tuple: (filename, DataFrame/text_content) or (None, None).
    """
    st.sidebar.header("1. Upload Your Data")
    uploaded_file = st.sidebar.file_uploader(
        "Upload a CSV, TSV, Excel (.xlsx/.xls), or PDF file",
        type=["csv", "tsv", "xlsx", "xls", "pdf"],
        accept_multiple_files=False # Limit to single file upload
    )

    if uploaded_file:
        file_name = uploaded_file.name
        st.sidebar.write(f"**Processing:** {file_name}")

        # Determine file type and load accordingly
        if file_name.endswith(('.csv', '.tsv')):
            delimiter_option = st.sidebar.radio(
                f"Select delimiter for {file_name}:",
                ('Comma (,)', 'Tab (\t)'),
                key=f"delimiter_{file_name}"
            )
            delimiter = ',' if delimiter_option == 'Comma (,)' else '\t'
            df = load_csv_tsv(uploaded_file, delimiter)
            if df is not None:
                return file_name, df
        elif file_name.endswith(('.xlsx', '.xls')):
            df = load_excel(uploaded_file)
            if df is not None:
                return file_name, df
        elif file_name.endswith('.pdf'):
            # Option to attempt table extraction for PDF
            attempt_table_extraction = st.sidebar.checkbox(
                "Attempt table extraction from PDF (requires Camelot & Ghostscript)",
                value=True, # Default to true for convenience
                key=f"pdf_extract_option_{file_name}"
            )
            pdf_data = extract_from_pdf(uploaded_file, attempt_table_extraction)
            if pdf_data['type'] == 'dataframe':
                return file_name, pdf_data['content']
            elif pdf_data['type'] == 'text':
                return file_name, pdf_data['content']
            else:
                return None, None # No content extracted
    return None, None # No file uploaded or error

# --- Data Quality Analysis Functions ---

def analyze_dataframe_quality(df_name, df):
    """
    Analyzes a Pandas DataFrame for common data quality issues.
    Returns a dictionary of findings.
    """
    findings = {
        "missing_values": {},
        "duplicate_rows_count": 0,
        "inconsistent_categorical": {},
        "incorrect_datatypes": {},
        "whitespace_issues": {},
        "outliers": {}, # New: For numerical outliers
        "uniqueness_violations": {}, # New: For columns that should be unique
        "date_format_inconsistencies": {} # New: For mixed date formats
    }

    st.subheader(f"Data Quality Report for: `{df_name}`")

    # 1. Missing Values
    missing_counts = df.isnull().sum()
    missing_cols = missing_counts[missing_counts > 0]
    if not missing_cols.empty:
        st.warning("⚠️ Missing Values Detected!")
        st.dataframe(missing_cols.to_frame(name='Missing Count'))
        findings["missing_values"] = missing_cols.to_dict()
    else:
        st.success("✅ No missing values found.")

    # 2. Duplicate Rows (entire row duplicates)
    duplicate_rows = df.duplicated().sum()
    if duplicate_rows > 0:
        st.warning(f"⚠️ {duplicate_rows} duplicate row(s) detected!")
        findings["duplicate_rows_count"] = duplicate_rows
    else:
        st.success("✅ No duplicate rows found.")

    # 3. Inconsistent Categorical Values (e.g., casing, extra spaces)
    # Iterate through object/string columns to check for inconsistencies
    for col in df.select_dtypes(include=['object']).columns:
        unique_values = df[col].dropna().astype(str).unique()
        # Check for leading/trailing spaces
        if any(val != val.strip() for val in unique_values):
            findings["whitespace_issues"][col] = "Leading/trailing whitespace detected."
        # Check for casing inconsistencies (after stripping whitespace)
        cleaned_unique_values = {val.strip().lower() for val in unique_values}
        if len(cleaned_unique_values) < len(unique_values):
            findings["inconsistent_categorical"][col] = "Casing or other minor variations detected (e.g., 'Male' vs 'male')."

    if findings["inconsistent_categorical"] or findings["whitespace_issues"]:
        st.warning("⚠️ Potential Inconsistencies in Categorical/Text Data:")
        if findings["whitespace_issues"]:
            st.write("   - **Whitespace Issues:**")
            for col, issue in findings["whitespace_issues"].items():
                st.write(f"     - Column `{col}`: {issue}")
        if findings["inconsistent_categorical"]:
            st.write("   - **Value Inconsistencies (Casing/Variations):**")
            for col, issue in findings["inconsistent_categorical"].items():
                st.write(f"     - Column `{col}`: {issue}")
    else:
        st.success("✅ Categorical/text data appears consistent (no obvious casing/whitespace issues).")

    # 4. Incorrect Data Types (basic check: numbers as objects)
    for col in df.columns:
        # Check if a numerical column is stored as object type
        if pd.api.types.is_object_dtype(df[col]) and pd.to_numeric(df[col], errors='coerce').notna().any():
            if not pd.to_numeric(df[col], errors='coerce').equals(df[col]): # Check if conversion changes values
                findings["incorrect_datatypes"][col] = "Numerical data stored as object/string type."

    if findings["incorrect_datatypes"]:
        st.warning("⚠️ Potential Incorrect Data Types:")
        for col, issue in findings["incorrect_datatypes"].items():
            st.write(f"   - Column `{col}`: {issue}")
    else:
        st.success("✅ Data types appear appropriate for most columns.")

    # 5. Outlier Detection (for numerical columns using IQR)
    numerical_cols = df.select_dtypes(include=['number']).columns
    if not numerical_cols.empty:
        outlier_detected = False
        for col in numerical_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col]
            if not outliers.empty:
                findings["outliers"][col] = {
                    "count": len(outliers),
                    "examples": outliers.head(5).tolist() # Show first 5 examples
                }
                outlier_detected = True
        if outlier_detected:
            st.warning("⚠️ Potential Outliers Detected in Numerical Data:")
            for col, info in findings["outliers"].items():
                st.write(f"   - Column `{col}`: {info['count']} outlier(s) detected (e.g., {info['examples']}).")
        else:
            st.success("✅ No obvious outliers detected in numerical columns (using IQR method).")
    else:
        st.info("No numerical columns found for outlier detection.")

    # 6. Uniqueness Violations (for columns that might be unique, like IDs)
    # This check assumes columns named 'ID', 'id', 'staffid', 'employeeid' etc. should be unique.
    # For a more robust app, you'd let the user specify unique key columns.
    potential_id_cols = [col for col in df.columns if 'id' in str(col).lower()]
    uniqueness_violation_found = False
    for col in potential_id_cols:
        if df[col].duplicated().any():
            duplicate_ids = df[col][df[col].duplicated()].unique()
            findings["uniqueness_violations"][col] = {
                "count": len(duplicate_ids),
                "examples": duplicate_ids.tolist()
            }
            uniqueness_violation_found = True

    if uniqueness_violation_found:
        st.warning("⚠️ Potential Uniqueness Violations Detected:")
        for col, info in findings["uniqueness_violations"].items():
            st.write(f"   - Column `{col}` (potential ID): {info['count']} duplicate ID(s) found (e.g., {info['examples']}).")
    else:
        st.success("✅ No obvious uniqueness violations found in potential ID columns.")

    # 7. Date Format Inconsistencies (basic check)
    date_inconsistency_found = False
    for col in df.select_dtypes(include=['object']).columns:
        # Attempt to convert to datetime, coercing errors
        temp_series = pd.to_datetime(df[col], errors='coerce')
        # If there are non-null values that couldn't be converted, it suggests mixed formats
        if temp_series.isnull().sum() > 0 and temp_series.notnull().any():
            # Check if all non-null original values could be parsed
            if not df[col][temp_series.isnull()].isnull().all():
                findings["date_format_inconsistencies"][col] = "Mixed or invalid date formats detected."
                date_inconsistency_found = True

    if date_inconsistency_found:
        st.warning("⚠️ Potential Date Format Inconsistencies:")
        for col, issue in findings["date_format_inconsistencies"].items():
            st.write(f"   - Column `{col}`: {issue}")
    else:
        st.success("✅ Date formats appear consistent or no date columns found.")


    return findings

# --- Cleaning Suggestion Function (UPDATED for Excel/Google Sheets) ---

def suggest_cleaning_actions(findings):
    """
    Suggests data cleaning actions based on the analysis findings,
    providing Excel/Google Sheet formulas and features.
    """
    st.subheader("Suggested Cleaning Actions (Excel/Google Sheets):")
    if not any(findings.values()): # Check if all finding categories are empty
        st.info("🎉 Your data appears quite clean! No major cleaning suggestions at this moment.")
        return

    st.info("Remember: For very large datasets or complex cleaning, programming tools like Python (with Pandas) are often more efficient.")

    # Missing Values Suggestions
    if findings["missing_values"]:
        st.markdown("---")
        st.markdown("### 🧹 Missing Values:")
        for col, count in findings["missing_values"].items():
            st.write(f"- Column `{col}` has **{count} empty cells**.")
            st.markdown(f"  - **Suggestion:**")
            st.markdown(f"    - **Manually fill:** For small numbers, you might fill them by hand if you know the correct values.")
            st.markdown(f"    - **Find & Replace:** Use 'Find & Replace' (Ctrl+H or Cmd+H) to replace common missing value indicators (like 'N/A', '-') with truly empty cells.")
            st.markdown(f"    - **Filter & Delete:** Filter the column for empty cells and delete those rows (if the missing data is not critical and count is small).")
            st.markdown(f"    - **Imputation (Advanced):** For numerical data, you might fill with the average (`=AVERAGE(A:A)`) or median of the column. For text, fill with the most common value. This often requires more manual steps in spreadsheets.")
            # Pandas equivalent: df['col'].fillna(df['col'].mean()), df['col'].dropna()

    # Duplicate Rows Suggestions
    if findings["duplicate_rows_count"] > 0:
        st.markdown("---")
        st.markdown("### 🧹 Duplicate Rows:")
        st.write(f"- Your dataset contains **{findings['duplicate_rows_count']} duplicate row(s)**.")
        st.markdown(f"  - **Suggestion:**")
        st.markdown(f"    - **Excel/Google Sheets Feature:** Use the 'Remove Duplicates' feature. In Excel: Data tab > Data Tools group > Remove Duplicates. In Google Sheets: Data > Data cleanup > Remove duplicates.")
            # Pandas equivalent: df.drop_duplicates(inplace=True)

    # Inconsistent Categorical/Whitespace Suggestions
    if findings["inconsistent_categorical"] or findings["whitespace_issues"]:
        st.markdown("---")
        st.markdown("### 🧹 Inconsistent Text/Categorical Data:")
        if findings["whitespace_issues"]:
            st.write("- **Leading/Trailing Whitespace:**")
            for col in findings["whitespace_issues"]:
                st.write(f"  - Column `{col}` has extra spaces at the beginning or end.")
                st.markdown(f"    - **Suggestion (Google Sheets/Excel Formula):** In a new column, use `=TRIM(A1)` (assuming data is in A1) and then copy-paste values back to the original column.")
                st.markdown(f"    - **Excel Feature:** Data tab > Data Tools group > Text to Columns (use 'Space' as delimiter, then delete extra columns).")
                # Pandas equivalent: df['col'].str.strip()
        if findings["inconsistent_categorical"]:
            st.write("- **Casing/Value Variations:**")
            for col in findings["inconsistent_categorical"]:
                st.write(f"  - Column `{col}` has inconsistent capitalization or slightly different ways of writing the same thing (e.g., 'Male' vs 'male').")
                st.markdown(f"    - **Suggestion (Google Sheets/Excel Formulas):** In a new column, convert text to a consistent case:")
                st.markdown(f"      - To all lowercase: `=LOWER(A1)`")
                st.markdown(f"      - To all uppercase: `=UPPER(A1)`")
                st.markdown(f"      - To Proper Case (first letter capitalized): `=PROPER(A1)`")
                st.markdown(f"      - After applying the formula, copy the new column and 'Paste Special > Values' back to the original column.")
                st.markdown(f"    - **Suggestion (Manual Correction):** For specific variations (e.g., 'M' vs 'Male'), use 'Find & Replace' (Ctrl+H or Cmd+H) to standardize values.")
                # Pandas equivalent: df['col'].str.lower(), df['col'].replace({'M': 'Male'})

    # Incorrect Data Types Suggestions
    if findings["incorrect_datatypes"]:
        st.markdown("---")
        st.markdown("### 🧹 Incorrect Data Types:")
        for col in findings["incorrect_datatypes"]:
            st.write(f"- Column `{col}` appears to be numbers (e.g., '123') but is stored as text. This can prevent calculations.")
            st.markdown(f"  - **Suggestion (Google Sheets/Excel Formula):** In a new column, use `=VALUE(A1)` (assuming text number is in A1) and then copy-paste values back to the original column.")
            st.markdown(f"  - **Excel Feature:** Select the column, then Data tab > Data Tools group > Text to Columns > Finish (this often forces conversion).")
            st.markdown(f"  - **Excel Feature:** Look for a small green triangle in the top-left of cells; click it and choose 'Convert to Number'.")
            # Pandas equivalent: pd.to_numeric(df['col'], errors='coerce')

    # Outlier Suggestions
    if findings["outliers"]:
        st.markdown("---")
        st.markdown("### 🧹 Potential Outliers:")
        st.write("Outliers are data points that significantly differ from other observations. They can be genuine or errors.")
        for col, info in findings["outliers"].items():
            st.write(f"- Column `{col}` has **{info['count']} potential outlier(s)** (e.g., {info['examples']}).")
            st.markdown(f"  - **Suggestion:**")
            st.markdown(f"    - **Review Manually:** Filter the column to see these values and decide if they are errors or legitimate extreme values.")
            st.markdown(f"    - **Correction/Removal:** If errors, correct them. If legitimate but skewing analysis, consider removing or transforming them (e.g., capping values).")
            # Pandas equivalent: df[(df['col'] >= lower_bound) & (df['col'] <= upper_bound)] or df['col'].clip(lower=lower_bound, upper=upper_bound)

    # Uniqueness Violations Suggestions
    if findings["uniqueness_violations"]:
        st.markdown("---")
        st.markdown("### 🧹 Uniqueness Violations:")
        st.write("Some columns, like IDs, should ideally contain only unique values.")
        for col, info in findings["uniqueness_violations"].items():
            st.write(f"- Column `{col}` has **{info['count']} duplicate ID(s)** (e.g., {info['examples']}).")
            st.markdown(f"  - **Suggestion:**")
            st.markdown(f"    - **Identify True Duplicates:** Determine if the entire row is a duplicate or just the ID. If only the ID, investigate why.")
            st.markdown(f"    - **Remove Duplicates:** If the entire row is a duplicate, use the 'Remove Duplicates' feature (as mentioned above) and select only the ID column to ensure uniqueness for that specific column.")
            # Pandas equivalent: df.drop_duplicates(subset=[col], inplace=True)

    # Date Format Inconsistencies Suggestions
    if findings["date_format_inconsistencies"]:
        st.markdown("---")
        st.markdown("### 🧹 Date Format Inconsistencies:")
        st.write("Dates in a column should ideally be in a consistent format for proper sorting and calculations.")
        for col, issue in findings["date_format_inconsistencies"].items():
            st.write(f"- Column `{col}`: {issue}")
            st.markdown(f"  - **Suggestion:**")
            st.markdown(f"    - **Text to Columns:** Use 'Text to Columns' with 'Date' option to try and parse various formats.")
            st.markdown(f"    - **Excel/Google Sheets Formulas:** Use formulas like `=TEXT(A1, \"YYYY-MM-DD\")` to convert dates to a standard text format, or `=DATEVALUE(A1)` to convert text dates to serial numbers (which can then be formatted).")
            st.markdown(f"    - **Manual Correction:** For a few inconsistent dates, manual correction might be easiest.")
            # Pandas equivalent: pd.to_datetime(df['col'], errors='coerce', format='...')

# --- New Function: auto_clean_dataframe ---
def auto_clean_dataframe(df, findings):
    """
    Performs automatic cleaning on the DataFrame based on detected findings.
    This applies common, relatively safe cleaning operations.
    """
    cleaned_df = df.copy() # Work on a copy to avoid modifying the original DataFrame directly

    st.subheader("Automated Cleaning Steps Applied:")

    # 1. Remove Duplicate Rows (entire row duplicates)
    if findings["duplicate_rows_count"] > 0:
        initial_rows = len(cleaned_df)
        cleaned_df.drop_duplicates(inplace=True)
        st.write(f"- Removed {initial_rows - len(cleaned_df)} duplicate row(s).")
    else:
        st.write("- No duplicate rows to remove.")

    # 2. Handle Whitespace Issues
    if findings["whitespace_issues"]:
        st.write("- Trimming leading/trailing whitespace from affected text columns:")
        for col in findings["whitespace_issues"]:
            if pd.api.types.is_object_dtype(cleaned_df[col]): # Ensure it's a string/object column
                cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                st.write(f"  - Trimmed whitespace in column `{col}`.")
    else:
        st.write("- No leading/trailing whitespace issues to fix.")

    # 3. Standardize Casing (to lowercase for simplicity in auto-clean)
    if findings["inconsistent_categorical"]:
        st.write("- Standardizing casing to lowercase for affected categorical columns:")
        for col in findings["inconsistent_categorical"]:
            if pd.api.types.is_object_dtype(cleaned_df[col]): # Ensure it's a string/object column
                cleaned_df[col] = cleaned_df[col].astype(str).str.lower()
                st.write(f"  - Converted column `{col}` to lowercase.")
    else:
        st.write("- No casing inconsistencies to fix (auto-converted to lowercase).")

    # 4. Correct Data Types (Numerical stored as object)
    if findings["incorrect_datatypes"]:
        st.write("- Converting detected numerical columns to numeric type:")
        for col in findings["incorrect_datatypes"]:
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
            st.write(f"  - Converted column `{col}` to numeric. Non-convertible values are now empty (NaN).")
    else:
        st.write("- No incorrect data types to fix.")

    # 5. Missing Values (Simple Auto-Imputation for demonstration)
    if findings["missing_values"]:
        st.write("- Handling missing values (simple imputation):")
        for col in findings["missing_values"]:
            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                # Fill numerical missing with mean
                mean_val = cleaned_df[col].mean()
                cleaned_df[col].fillna(mean_val, inplace=True)
                st.write(f"  - Filled missing numerical values in `{col}` with its mean ({mean_val:.2f}).")
            elif pd.api.types.is_object_dtype(cleaned_df[col]):
                # Fill categorical missing with mode (most frequent)
                mode_val = cleaned_df[col].mode()[0] if not cleaned_df[col].mode().empty else "Unknown"
                cleaned_df[col].fillna(mode_val, inplace=True)
                st.write(f"  - Filled missing categorical values in `{col}` with its mode ('{mode_val}').")
            else:
                st.write(f"  - Missing values in `{col}` (non-numeric/non-categorical) were not auto-filled.")
    else:
        st.write("- No missing values to auto-fill.")

    # Auto-clean for uniqueness violations in potential ID columns
    # This is a more aggressive auto-clean, so use with caution.
    if findings["uniqueness_violations"]:
        st.write("- Attempting to remove duplicates based on potential ID columns:")
        for col in findings["uniqueness_violations"]:
            initial_rows = len(cleaned_df)
            # Drop duplicates based on the specific column identified as having uniqueness violations
            cleaned_df.drop_duplicates(subset=[col], inplace=True)
            st.write(f"  - Removed {initial_rows - len(cleaned_df)} duplicate entries in column `{col}` to ensure uniqueness.")

    st.success("✨ Automated cleaning process completed!")
    return cleaned_df

# --- New Function: display_column_summary ---
def display_column_summary(df):
    """
    Displays a summary of each column's data type and key statistics.
    """
    st.header("4. Column Data Summary")
    st.info("This section provides a quick overview of each column's data type and key characteristics. This helps you understand your data at a glance and identify potential issues like unexpected unique values or ranges.")

    # Display overall DataFrame info
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    st.text(info_str)

    st.markdown("---")

    for col in df.columns:
        st.subheader(f"Column: `{col}`")
        st.write(f"**Data Type:** `{df[col].dtype}`")
        st.write(f"**Non-Null Count:** `{df[col].count()}`")
        st.write(f"**Missing Values:** `{df[col].isnull().sum()}`")

        if pd.api.types.is_numeric_dtype(df[col]):
            st.markdown("**Numerical Statistics:**")
            st.write(f"- **Mean:** `{df[col].mean():.2f}`")
            st.write(f"- **Median:** `{df[col].median():.2f}`")
            st.write(f"- **Min:** `{df[col].min():.2f}`")
            st.write(f"- **Max:** `{df[col].max():.2f}`")
            st.write(f"- **Standard Deviation:** `{df[col].std():.2f}`")
            st.write(f"- **Mode:** `{df[col].mode().tolist()}`") # Mode can be multiple
        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            st.markdown("**Categorical/Text Statistics:**")
            unique_count = df[col].nunique()
            st.write(f"- **Unique Values Count:** `{unique_count}`")
            st.write(f"- **Percentage Unique:** `{unique_count / len(df) * 100:.2f}%`")
            st.write(f"- **Top 5 Most Frequent Values:**")
            st.dataframe(df[col].value_counts().head(5).to_frame(name='Count'))
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            st.markdown("**Date/Time Statistics:**")
            st.write(f"- **Min Date:** `{df[col].min()}`")
            st.write(f"- **Max Date:** `{df[col].max()}`")
            st.write(f"- **Unique Dates Count:** `{df[col].nunique()}`")
        else:
            st.info("No specific statistics available for this data type.")
        st.markdown("---")


# --- Main Application Logic ---

def main():
    """
    Main function to run the Streamlit application.
    """
    st.title("📊 Data Quality & Cleaning Assistant")
    st.markdown("Upload your datasets to get an automated quality report and cleaning suggestions.")

    # Data upload in the sidebar (now returns single file_name, content)
    file_name, content = data_upload_sidebar()

    if file_name and content is not None:
        st.header("2. Data Preview & Analysis")
        st.markdown(f"---")
        st.markdown(f"### Previewing: `{file_name}`")

        current_df_for_analysis = None # This will hold the DataFrame to be analyzed and potentially auto-cleaned

        if isinstance(content, pd.DataFrame):
            # --- PDF Table Header Correction Logic ---
            if file_name.endswith('.pdf'):
                st.info("💡 **PDF Table Extraction Note:** If headers are incorrect (e.g., numerical), use the slider below to select the correct header row.")

                # Display initial DataFrame from PDF
                st.dataframe(content)

                # Allow user to select header row
                header_row_index = st.number_input(
                    "Enter row index for headers (0-indexed, e.g., 0 for first row):",
                    min_value=0,
                    max_value=len(content) - 1,
                    value=0, # Default to 0, assuming headers are often in the first row
                    key=f"header_select_{file_name}"
                )

                # Apply new headers if different from current
                if header_row_index >= 0 and header_row_index < len(content):
                    new_header = content.iloc[header_row_index] # Grab the row for the header
                    # Check for duplicate headers after cleaning, append suffix if needed
                    seen_headers = {}
                    cleaned_new_header = []
                    for h in new_header:
                        h_str = str(h).strip() # Strip whitespace from header
                        if h_str in seen_headers:
                            seen_headers[h_str] += 1
                            cleaned_new_header.append(f"{h_str}_{seen_headers[h_str]}")
                        else:
                            seen_headers[h_str] = 0 # Initialize count
                            cleaned_new_header.append(h_str)

                    df_with_correct_headers = content[header_row_index + 1:].copy() # All rows after header
                    df_with_correct_headers.columns = cleaned_new_header # Set the new header
                    df_with_correct_headers.reset_index(drop=True, inplace=True) # Reset index

                    st.subheader("DataFrame with Corrected Headers:")
                    st.dataframe(df_with_correct_headers.head())
                    st.write(f"Shape: {df_with_correct_headers.shape[0]} rows, {df_with_correct_headers.shape[1]} columns")

                    # This is the DataFrame that will be analyzed and potentially auto-cleaned
                    current_df_for_analysis = df_with_correct_headers
                else:
                    st.warning("Invalid header row index selected. Using original extracted data.")
                    st.write(f"Shape: {content.shape[0]} rows, {content.shape[1]} columns")
                    current_df_for_analysis = content # Use original if header selection is invalid


            else: # For CSV/TSV/Excel, just show head and shape
                st.dataframe(content.head()) # Show first 5 rows of DataFrame
                st.write(f"Shape: {content.shape[0]} rows, {content.shape[1]} columns")
                current_df_for_analysis = content # For other file types, the original content is the one to analyze

            # Add download option for the initially processed DataFrame
            csv_buffer_original = io.StringIO()
            current_df_for_analysis.to_csv(csv_buffer_original, index=False)
            st.download_button(
                label="Download Current Data as CSV",
                data=csv_buffer_original.getvalue(),
                file_name=f"{file_name.split('.')[0]}_current_data.csv",
                mime="text/csv",
            )

            # Display column summary BEFORE quality analysis and cleaning suggestions
            display_column_summary(current_df_for_analysis)

            # Perform data quality analysis and suggest cleaning actions
            quality_findings = analyze_dataframe_quality(file_name, current_df_for_analysis)
            suggest_cleaning_actions(quality_findings)

            # --- Auto Cleaning Section ---
            st.markdown("---")
            st.header("5. Automated Data Cleaning") # Updated header number
            if st.button("✨ Auto Clean Data"):
                with st.spinner("Applying automated cleaning steps..."):
                    cleaned_df = auto_clean_dataframe(current_df_for_analysis, quality_findings)

                st.subheader("Cleaned Data Preview:")
                st.dataframe(cleaned_df.head())
                st.write(f"Shape of Cleaned Data: {cleaned_df.shape[0]} rows, {cleaned_df.shape[1]} columns")

                # Add download option for the cleaned DataFrame
                csv_buffer_cleaned = io.StringIO()
                cleaned_df.to_csv(csv_buffer_cleaned, index=False)
                st.download_button(
                    label="Download Cleaned Data as CSV",
                    data=csv_buffer_cleaned.getvalue(),
                    file_name=f"{file_name.split('.')[0]}_auto_cleaned.csv",
                    mime="text/csv",
                )
                st.success("Cleaned data is ready for download!")
            else:
                st.info("Click 'Auto Clean Data' to apply basic automated cleaning steps.")


        elif isinstance(content, str): # Handle PDF text content
            st.text_area(f"Text Content from '{file_name}' (first 500 chars):", content[:500], height=200)
            st.info("💡 **Note on PDF:** This is raw text. For structured tables, manual copy/paste or specialized tools (like `pdfplumber`, `camelot-py`) are typically required for accurate extraction.")

        st.markdown("---") # Separator after file analysis

    else:
        st.info("Please upload a data file using the sidebar to get started!")

# Run the app
if __name__ == "__main__":
    main() # Corrected: Call the main function
