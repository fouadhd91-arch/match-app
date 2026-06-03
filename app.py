import streamlit as st
import pandas as pd
import re
import pdfplumber
from datetime import datetime
import io
import time

st.set_page_config(page_title="منظومة مطابقة الحسابات والتأمين", layout="wide")

# حفظ حالة التبويب النشط والبيانات المسحوبة في الذاكرة لتسهيل الحركة والتنقل
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "bank"

if "parsed_bank_df" not in st.session_state:
    st.session_state.parsed_bank_df = None

# كود CSS مخصص لضغط المسافات، تلوين الأزرار بنظام 3D، وحل مشكلة تداخل uploadpload بالكامل
st.markdown("""
    <style>
    /* استيراد ودمج خط Cairo الاحترافي لجميع عناصر الويب */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, button, span, label, input, select {
        font-family: 'Cairo', sans-serif !important;
    }
    
    /* محاذاة الصفحة لتناسب اللغة العربية */
    .reportview-container { direction: RTL; text-align: right; }
    .stMarkdown, .stText, .stRadio, .stSelectbox, .stButton, .stProgress, label { 
        direction: RTL; 
        text-align: right; 
    }
    
    /* إلغاء وضغط المساحات الفارغة والفراغات المتباعدة على الهاتف بالكامل */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
    div[data-testid="stVerticalBlock"] > div {
        padding-top: 1px !important;
        padding-bottom: 1px !important;
        margin-top: 1px !important;
        margin-bottom: 1px !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 4px !important;
    }
    
    /* إجبار أزرار ومربعات الهاتف على البقاء أفقياً (جنب بعض) دون أن تتراكم عمودياً */
    [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        gap: 6px !important;
        flex-wrap: nowrap !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        min-width: 0 !important;
        flex: 1 !important;
    }
    
    /* أزرار التنقل العلوية - تصميم 3D مميز ومختلف الألوان */
    /* الزر الفعال (المضغوط عليه حالياً) يظهر باللون الأخضر الثري */
    .btn-active button {
        background-color: #2e7d32 !important; 
        color: white !important;
        font-size: 14px !important;
        height: 2.8em !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 0 #1b5e20, 0 6px 8px rgba(0,0,0,0.2) !important; /* تأثير ثلاثي الأبعاد */
        transform: translateY(-2px) !important;
    }
    .btn-active button:active {
        transform: translateY(1px) !important;
        box-shadow: 0 1px 0 #1b5e20 !important;
    }
    
    /* الزر غير الفعال (الآخر) يظهر باللون الأحمر الثري */
    .btn-inactive button {
        background-color: #c62828 !important; 
        color: white !important;
        font-size: 14px !important;
        height: 2.8em !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 0 #8e0000, 0 6px 8px rgba(0,0,0,0.2) !important; /* تأثير ثلاثي الأبعاد */
        transform: translateY(-2px) !important;
    }
    .btn-inactive button:active {
        transform: translateY(1px) !important;
        box-shadow: 0 1px 0 #8e0000 !important;
    }
    
    /* زر البحث الأخضر - تصميم 3D */
    .search-btn-container button {
        background-color: #4caf50 !important;
        color: white !important;
        font-size: 15px !important;
        height: 2.5em !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 0 #1b5e20, 0 5px 6px rgba(0,0,0,0.15) !important;
        transform: translateY(-2px) !important;
    }
    .search-btn-container button:active {
        transform: translateY(1px) !important;
        box-shadow: 0 1px 0 #1b5e20 !important;
    }
    
    /* زر المقارنة البرتقالي - تصميم 3D */
    .compare-btn-container button {
        background-color: #ff9800 !important;
        color: white !important;
        font-size: 16px !important;
        height: 2.8em !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 0 #e65100, 0 5px 6px rgba(0,0,0,0.15) !important;
        transform: translateY(-2px) !important;
    }
    .compare-btn-container button:active {
        transform: translateY(1px) !important;
        box-shadow: 0 1px 0 #e65100 !important;
    }
    
    /* حل مشكلة تداخل وتكرار كلمة upload وإخفاء التفاصيل الإنجليزية الزائدة */
    div[data-testid="stFileUploader"] section {
        padding: 6px !important;
        background-color: #1a1c1e !important;
        border: 2px dashed #4caf50 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stFileUploader"] section button {
        background-color: #4caf50 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: none !important;
        box-shadow: 0 3px 0 #1b5e20 !important; /* زر رفع 3D */
    }
    /* إخفاء نصوص الرفع الإنجليزية المتداخلة تلقائياً */
    div[data-testid="stFileUploader"] section > div {
        display: none !important;
    }
    /* استبدالها بجملة إرشادية عربية واحدة ونظيفة */
    div[data-testid="stFileUploader"] section::after {
        content: "اضغط هنا لاختيار الملف" !important;
        display: block !important;
        color: #aaa !important;
        font-size: 13px !important;
        text-align: center !important;
        margin-top: 6px !important;
        font-family: 'Cairo', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# دالة تنظيف واستخلاص الأسماء بدقة
def clean_name(text):
    if not text:
        return "غير معروف"
    text_clean = str(text)
    text_lower = text_clean.lower()
    
    start_idx = -1
    for marker in ["amir=", "amir:", "amir "]:
        idx = text_lower.find(marker)
        if idx != -1:
            start_idx = idx + len(marker)
            break
            
    if start_idx == -1:
        return "غير معروف"
        
    end_idx = -1
    for marker in ["aciklama", "açıklama", "lehdar", "gönd.bank"]:
        idx = text_lower.find(marker, start_idx)
        if idx != -1:
            end_idx = idx
            break
            
    if end_idx != -1:
        name = text_clean[start_idx:end_idx].strip()
    else:
        name = text_clean[start_idx:].strip()
        
    name = re.sub(r"[=\-_:]", "", name).strip()
    name = " ".join(name.split())
    return name if name else "غير معروف"

def parse_turkish_bank_pdf(pdf_file):
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, page in enumerate(pdf.pages):
            percent_complete = int(((idx + 1) / total_pages) * 100)
            progress_bar.progress(percent_complete)
            status_text.markdown(f"<p style='color: #4caf50; font-size: 12px; font-weight: bold;'>⏳ جاري قراءة الصفحة {idx + 1} من {total_pages}...</p>", unsafe_allow_html=True)
            
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 3:
                        date_str = row[0]
                        if date_str and re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str.strip()):
                            all_rows.append(row[:3])
            time.sleep(0.04)
            
        progress_bar.empty()
        status_text.empty()
        
    df = pd.DataFrame(all_rows, columns=["İşlem Tarihi", "Açıklama", "Tutar"])
    df["Tutar_Clean"] = df["Tutar"].str.replace(" TL", "").str.replace(".", "").str.replace(",", ".").astype(float)
    df["İşlem Tarihi"] = pd.to_datetime(df["İşlem Tarihi"], format="%d.%m.%Y")
    
    # المحافظة التامة على الترتيب الفعلي لـ PDF سطر بسطر
    
    types = []
    for i in range(len(df)):
        desc = str(df.loc[i, "Açıklama"]).lower()
        if "amir" in desc:
            if "lehdar" in desc and "nurer" not in desc:
                types.append("خارج")
            else:
                types.append("داخل")
        elif "lehdar" in desc:
            if "nurer" in desc:
                types.append("داخل")
            else:
                types.append("خارج")
        elif "borç" in desc or "giden" in desc or "ödeme" in desc:
            types.append("خارج")
        else:
            types.append("داخل")
            
    df["نوع الحوالة"] = types
    df["اسم المحوّل"] = df["Açıklama"].apply(clean_name)
    return df


# ==================== أزرار التنقل العلوية الكبيرة (جنب بعض أفقياً ومختلفة الألوان) ====================
st.write(" ")
col_nav1, col_nav2 = st.columns(2)

with col_nav1:
    is_active = st.session_state.active_tab == "bank"
    btn_style = "btn-active" if is_active else "btn-inactive"
    st.markdown(f'<div class="{btn_style}">', unsafe_allow_html=True)
    if st.button("كشف الحساب", key="btn_bank_nav", use_container_width=True):
        st.session_state.active_tab = "bank"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_nav2:
    is_active = st.session_state.active_tab == "insurance"
    btn_style = "btn-active" if is_active else "btn-inactive"
    st.markdown(f'<div class="{btn_style}">', unsafe_allow_html=True)
    if st.button("مطابقة التأمين", key="btn_ins_nav", use_container_width=True):
        st.session_state.active_tab = "insurance"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.write("---")


# ==================== الصفحة الأولى: كشف الحساب البنكي ====================
if st.session_state.active_tab == "bank":
    st.markdown("<h4 style='font-size: 16px; font-weight: bold; margin-bottom: 2px;'>كشف الحوالات</h4>", unsafe_allow_html=True)
    
    col_file, col_btn = st.columns([3, 1])
    
    with col_file:
        bank_file = st.file_uploader("رفع الملف", type=["pdf"], key="bank_pdf_uploader")
        
    with col_btn:
        st.write("##") # محاذاة
        st.markdown('<div class="search-btn-container">', unsafe_allow_html=True)
        search_clicked = st.button("🔍 بحث", key="search_bank_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    if bank_file is None:
        st.session_state.parsed_bank_df = None
        
    if bank_file is not None and search_clicked:
        try:
            df_bank = parse_turkish_bank_pdf(bank_file)
            st.session_state.parsed_bank_df = df_bank
            st.success("تم الانتهاء من سحب ومعالجة الحوالات بنجاح!")
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الملف. التفاصيل: {str(e)}")
            
    if st.session_state.parsed_bank_df is not None:
        df_bank = st.session_state.parsed_bank_df
        
        st.markdown("<h4 style='font-size: 14px; font-weight: bold; margin-bottom: 1px;'>🔍 فلتر</h4>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("من تاريخ", df_bank["İşlem Tarihi"].min().date(), key="b_start")
        with col2:
            end_date = st.date_input("إلى تاريخ", df_bank["İşlem Tarihi"].max().date(), key="b_end")
        with col3:
            op_type = st.selectbox("المصدر", ["الكل", "داخل", "خارج"], key="b_type")
            
        search_query = st.text_input("🔍 بحث باسم الشخص الحقيقي الذي حوّل", key="b_search")
        
        # تطبيق التصفية
        filtered_df = df_bank[
            (df_bank["İşlem Tarihi"].dt.date >= start_date) & 
            (df_bank["İşlem Tarihi"].dt.date <= end_date)
        ]
        if op_type != "الكل":
            filtered_df = filtered_df[filtered_df["نوع الحوالة"] == op_type]
        if search_query:
            filtered_df = filtered_df[filtered_df["اسم المحوّل"].str.contains(search_query, case=False, na=False)]
            
        total_count = len(filtered_df)
        total_sum = filtered_df["Tutar_Clean"].sum()
        
        # عرض الإحصائيات في صندوقين مستقلين ملونين (أزرق صافي وأخضر صافي) وبدون أي رموز
        col_card1, col_card2 = st.columns(2)
        with col_card1:
            st.markdown(f"""
                <div style="background-color: #1565c0; padding: 10px; border-radius: 8px; text-align: center; box-shadow: 0 4px 0 #0d47a1, 0 6px 8px rgba(0,0,0,0.15); margin-bottom: 10px;">
                    <span style="color: #ffffff; font-size: 14px; font-weight: bold; display: block; margin-bottom: 2px;">العدد</span>
                    <span style="color: #ffffff; font-size: 20px; font-weight: bold;">{total_count} حركة</span>
                </div>
            """, unsafe_allow_html=True)
        with col_card2:
            st.markdown(f"""
                <div style="background-color: #2e7d32; padding: 10px; border-radius: 8px; text-align: center; box-shadow: 0 4px 0 #1b5e20, 0 6px 8px rgba(0,0,0,0.15); margin-bottom: 10px;">
                    <span style="color: #ffffff; font-size: 14px; font-weight: bold; display: block; margin-bottom: 2px;">مبلغ الحوالات</span>
                    <span style="color: #ffffff; font-size: 20px; font-weight: bold;">{total_sum:,.2f} TL</span>
                </div>
            """, unsafe_allow_html=True)
            
        display_df = pd.DataFrame({
            "تاريخ الحوالة": filtered_df["İşlem Tarihi"].dt.strftime('%Y-%m-%d'),
            "اسم الشخص الذي حوّل": filtered_df["اسم المحوّل"],
            "مبلغ الحوالة": filtered_df["Tutar"]
        })
        st.markdown("<h4 style='font-size: 13px; font-weight: bold; margin-bottom: 2px; margin-top: 10px;'>📋 الحوالات:</h4>", unsafe_allow_html=True)
        st.dataframe(display_df, use_container_width=True)


# ==================== الصفحة الثانية: مطابقة ملفات التأمين ====================
elif st.session_state.active_tab == "insurance":
    st.markdown("<h4 style='font-size: 16px; font-weight: bold; margin-bottom: 10px;'>مطابقة ملفات التأمين</h4>", unsafe_allow_html=True)
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        file1 = st.file_uploader("رفع ملف الأكسل (الاول):", type=["xlsx", "xls"], key="file1_up")
    with col_up2:
        file2 = st.file_uploader("رفع ملف الأكسل (الثاني):", type=["xlsx", "xls"], key="file2_up")
        
    if file1 and file2:
        try:
            df1 = pd.read_excel(file1)
            df2 = pd.read_excel(file2)
            if df1.shape[1] < 2 or df2.shape[1] < 2:
                st.error("يرجى التأكد من أن كلا الملفين يحتويان على عمودين على الأقل (نوع التأمين ورقم التأمين).")
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
                
                # زر مقارنة التأمين البرتقالي الكبير والجميل بتأثير 3D ثلاثي الأبعاد
                st.markdown('<div class="compare-btn-container">', unsafe_allow_html=True)
                compare_clicked = st.button("🔄 بدء مطابقة الأرقام وكشف النواقص", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if compare_clicked:
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
