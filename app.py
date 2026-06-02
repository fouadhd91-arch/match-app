import streamlit as st
import pandas as pd
import re
import pdfplumber
from datetime import datetime
import io

st.set_page_config(page_title="منظومة مطابقة الحسابات والتأمين", layout="wide")

st.markdown("""
    <style>
    .reportview-container { direction: RTL; text-align: right; }
    .stMarkdown, .stText, .stRadio, .stSelectbox, .stButton { direction: RTL; text-align: right; }
    div.stButton > button:first-child { background-color: #007bff; color: white; border-radius: 8px; padding: 0.5rem 2rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def clean_name(text):
    if not text: return ""
    match = re.search(r"Amir[=\s:](.*?)(?:Aciklama|Lehdar|$)", text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        name = re.sub(r"[=\-_:]", "", name)
        return " ".join(name.split())
    return "غير معروف"

def parse_turkish_bank_pdf(pdf_file):
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 5:
                        date_str = row[0]
                        if date_str and re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str.strip()):
                            all_rows.append(row[:5])
    df = pd.DataFrame(all_rows, columns=["İşlem Tarihi", "Açıklama", "Tutar", "Bakiye", "Referans Numarası"])
    df["Tutar_Clean"] = df["Tutar"].str.replace(" TL", "").str.replace(".", "").str.replace(",", ".").astype(float)
    df["Bakiye_Clean"] = df["Bakiye"].str.replace(" TL", "").str.replace(".", "").str.replace(",", ".").astype(float)
    df["İşlem Tarihi"] = pd.to_datetime(df["İşlem Tarihi"], format="%d.%m.%Y")
    df = df.sort_values(by=["İşlem Tarihi", "Referans Numarası"], ascending=True).reset_index(drop=True)
    types = []
    for i in range(len(df)):
        if i == 0: types.append("داخل")
        else:
            diff = df.loc[i, "Bakiye_Clean"] - df.loc[i-1, "Bakiye_Clean"]
            if diff > 0: types.append("داخل")
            else: types.append("خارج")
    df["نوع الحوالة"] = types
    df["اسم المحوّل"] = df["Açıklama"].apply(clean_name)
    df = df.sort_values(by=["İşlem Tarihi", "Referans Numarası"], ascending=False).reset_index(drop=True)
    return df

tab1, tab2 = st.tabs(["📊 تحليل كشف الحساب البنكي", "🔍 مطابقة ملفات التأمين"])

with tab1:
    st.header("تحليل وفلترة كشف الحساب البنكي (Vakıf Katılım)")
    bank_file = st.file_uploader("ارفع كشف الحساب بصيغة PDF", type=["pdf"])
    if bank_file:
        try:
            df_bank = parse_turkish_bank_pdf(bank_file)
            st.success("تمت معالجة الملف واستخراج العمليات بنجاح!")
            col1, col2, col3 = st.columns(3)
            with col1: start_date = st.date_input("من تاريخ", df_bank["İşlem Tarihi"].min().date())
            with col2: end_date = st.date_input("إلى تاريخ", df_bank["İşlem Tarihi"].max().date())
            with col3: op_type = st.selectbox("نوع الحوالة المطلوبة", ["الكل", "داخل", "خارج"])
            search_query = st.text_input("🔍 بحث باسم الشخص الذي حوّل")
            filtered_df = df_bank[(df_bank["İşlem Tarihi"].dt.date >= start_date) & (df_bank["İşlem Tarihi"].dt.date <= end_date)]
            if op_type != "الكل": filtered_df = filtered_df[filtered_df["نوع الحوالة"] == op_type]
            if search_query: filtered_df = filtered_df[filtered_df["اسم المحوّل"].str.contains(search_query, case=False, na=False)]
            inflows_only = filtered_df[filtered_df["نوع الحوالة"] == "داخل"]
            total_inflows = inflows_only["Tutar_Clean"].sum()
            st.markdown(f"""
                <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 20px;">
                    <h4 style="color: #155724; margin: 0; text-align: right;">💵 إجمالي المبلغ الداخل (للفترة المحددة):</h4>
                    <p style="font-size: 28px; font-weight: bold; color: #155724; margin: 10px 0 0 0; text-align: right;">{total_inflows:,.2f} TL</p>
                </div>
            """, unsafe_allow_html=True)
            display_df = pd.DataFrame({
                "تاريخ الحوالة": filtered_df["İşlem Tarihi"].dt.strftime('%Y-%m-%d'),
                "اسم الشخص الذي حوّل": filtered_df["اسم المحوّل"],
                "داخل أو خارج": filtered_df["نوع الحوالة"],
                "مبلغ الحوالة": filtered_df["Tutar"]
            })
            st.write("### جدول تفاصيل الحوالات المفلترة:")
            st.dataframe(display_df, use_container_width=True)
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة الكشف. التفاصيل: {str(e)}")

with tab2:
    st.header("مطابقة ملفات التأمين الثنائية")
    st.markdown("""
        <div style="background-color: #e2f0fd; padding: 15px; border-radius: 8px; border-right: 5px solid #007bff; margin-bottom: 20px; text-align: right;">
            <h5 style="color: #004085; margin: 0; font-weight: bold;">⚠️ تنبيه وإرشادات قبل الرفع:</h5>
            <p style="color: #004085; margin: 8px 0 0 0;">
                يرجى التأكد من تنظيم ملفات الإكسل بحيث يحتوي <b>الملف الأول</b> و <b>الملف الثاني</b> على الترتيب التالي:<br>
                1. <b>العمود الأول (A):</b> نوع التأمين (مثال: تأمين سيارات).<br>
                2. <b>العمود الثاني (B):</b> رقم التأمين (مثال: 12345).<br>
                <i>ملاحظة: سيتم تلقائياً اعتبار السطر الأول كعنوان (رأس جدول) وسيتم استثناؤه من حسابات المقارنة.</i>
            </p>
        </div>
    """, unsafe_allow_html=True)
    col_up1, col_up2 = st.columns(2)
    with col_up1: file1 = st.file_uploader("📂 ارفع ملف الإكسل: (الملف الأول)", type=["xlsx", "xls"], key="file1_up")
    with col_up2: file2 = st.file_uploader("📂 ارفع ملف الإكسل: (الملف الثاني)", type=["xlsx", "xls"], key="file2_up")
    if file1 and file2:
        try:
            df1 = pd.read_excel(file1)
            df2 = pd.read_excel(file2)
            if df1.shape[1] < 2 or df2.shape[1] < 2:
                st.error("يرجى التأكد من أن كلا الملفين المرفوعين يحتويان على عمودين على الأقل (نوع التأمين ورقم التأمين).")
            else:
                df1.columns = ["Insurance_Type", "Insurance_Number"] + list(df1.columns[2:])
                df2.columns = ["Insurance_Type", "Insurance_Number"] + list(df2.columns[2:])
                st.write("### معاينة البيانات المرفوعة (الجدول رباعي الأعمدة):")
                max_len = max(len(df1), len(df2))
                df1_padded = df1.reindex(range(max_len))
                df2_padded = df2.reindex(range(max_len))
                preview_df = pd.DataFrame({
                    "نوع التأمين للملف الأول": df1_padded["Insurance_Type"],
                    "رقم التأمين للملف الأول": df1_padded["Insurance_Number"],
                    "نوع التأمين للملف الثاني": df2_padded["Insurance_Type"],
                    "رقم التأمين للملف الثاني": df2_padded["Insurance_Number"]
                })
                st.dataframe(preview_df, use_container_width=True)
                st.write("---")
                if st.button("🔄 بدء مطابقة الأرقام وكشف النواقص"):
                    with st.spinner("جاري مطابقة أرقام التأمين واستخراج الفروقات..."):
                        nums_f1 = set(df1["Insurance_Number"].dropna().astype(str).str.strip())
                        nums_f2 = set(df2["Insurance_Number"].dropna().astype(str).str.strip())
                        not_in_f2 = nums_f1 - nums_f2
                        not_in_f1 = nums_f2 - nums_f1
                        list_not_in_f2 = list(not_in_f2)
                        list_not_in_f1 = list(not_in_f1)
                        diff_len = max(len(list_not_in_f2), len(list_not_in_f1))
                        list_not_in_f2_padded = list_not_in_f2 + [None] * (diff_len - len(list_not_in_f2))
                        list_not_in_f1_padded = list_not_in_f1 + [None] * (diff_len - len(list_not_in_f1))
                        results_df = pd.DataFrame({
                            "أرقام تأمين بالملف الأول (غير موجودة بالملف الثاني)": list_not_in_f2_padded,
                            "أرقام تأمين بالملف الثاني (غير موجودة بالملف الأول)": list_not_in_f1_padded
                        })
                        st.write("### 📋 جدول نتائج المطابقة والاختلافات:")
                        st.dataframe(results_df, use_container_width=True)
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            results_df.to_excel(writer, index=False, sheet_name='نواقص المطابقة')
                        processed_data = output.getvalue()
                        st.download_button(
                            label="📥 تحميل جدول النواقص كملف Excel",
                            data=processed_data,
                            file_name="نواقص_مطابقة_التأمين.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة ملفات الإكسل. التفاصيل: {str(e)}")
