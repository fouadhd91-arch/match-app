import streamlit as st
import pandas as pd
import re
import pdfplumber
from datetime import datetime
import io
import time

st.set_page_config(page_title="منظومة مطابقة الحسابات والتأمين", layout="wide")

# حفظ حالة التبويب النشط والبيانات المسحوبة في الذاكرة لتسهيل الحركة
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "bank"

if "parsed_bank_df" not in st.session_state:
    st.session_state.parsed_bank_df = None

# كود CSS مخصص لتجميل الواجهة بالكامل ودمج خط Cairo ومؤشر التحميل الأخضر
st.markdown("""
    <style>
    /* استيراد ودمج خط Cairo العربي الاحترافي لجميع عناصر الويب */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, button, span {
        font-family: 'Cairo', sans-serif !important;
    }
    
    /* محاذاة الصفحة لتناسب اللغة العربية */
    .reportview-container { direction: RTL; text-align: right; }
    .stMarkdown, .stText, .stRadio, .stSelectbox, .stButton, .stProgress { direction: RTL; text-align: right; }
    
    /* تجميل وتكبير أزرار التنقل العلوية الكبيرة الملونة */
    .nav-btn-bank button {
        background-color: #2e7d32 !important; /* أخضر مريح */
        color: white !important;
        font-size: 20px !important;
        height: 3.2em !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    .nav-btn-ins button {
        background-color: #1565c0 !important; /* أزرق مريح */
        color: white !important;
        font-size: 20px !important;
        height: 3.2em !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    /* تمييز الزر الفعال بإطار برتقالي خفيف */
    .nav-active button {
        border: 4px solid #ff9800 !important;
        transform: scale(1.02);
    }
    
    /* تلوين زر البحث الأخضر */
    .search-btn-container button {
        background-color: #4caf50 !important;
        color: white !important;
        font-size: 18px !important;
        height: 2.8em !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 3px 5px rgba(0,0,0,0.1) !important;
    }
    
    /* تلوين زر مقارنة التأمين باللون البرتقالي الجميل */
    .compare-btn-container button {
        background-color: #ff9800 !important;
        color: white !important;
        font-size: 18px !important;
        height: 3em !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    /* تغيير لون حز التحميل التفاعلي إلى الأخضر */
    .stProgress > div > div > div > div {
        background-color: #2e7d32 !important;
    }
    
    /* تنسيق خاص لبطاقات الحوالات القابلة للتمدد */
    .st-expander {
        border: 1px solid #e0e0e0 !important;
        border-right: 5px solid #4caf50 !important; /* حز أخضر جانبي مالي لكل بطاقة */
        border-radius: 8px !important;
        margin-bottom: 10px !important;
        background-color: #fafafa !important;
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
    # دمج الأسطر المتعددة (حتى 4 أسطر) في سطر واحد نظيف بدون فراغات زائدة
    name = " ".join(name.split())
    return name if name else "غير معروف"


# ==================== شريط الأزرار العلوية الكبيرة لسهولة التنقل ====================
st.write(" ")
col_nav1, col_nav2 = st.columns(2)

with col_nav1:
    st.markdown('<div class="nav-btn-bank' + (' nav-active' if st.session_state.active_tab == 'bank' else '') + '">', unsafe_allow_html=True)
    if st.button("📊 كشف الحساب البنكي (Vakıf)", key="btn_bank_nav", use_container_width=True):
        st.session_state.active_tab = "bank"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_nav2:
    st.markdown('<div class="nav-btn-ins' + (' nav-active' if st.session_state.active_tab == 'insurance' else '') + '">', unsafe_allow_html=True)
    if st.button("🔍 مطابقة ملفات التأمين", key="btn_ins_nav", use_container_width=True):
        st.session_state.active_tab = "insurance"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.write("---")


# ==================== الصفحة الأولى: كشف الحساب البنكي ====================
if st.session_state.active_tab == "bank":
    st.markdown("<h2 style='text-align: right;'>تحليل كشف الحساب البنكي</h2>", unsafe_allow_html=True)
    
    col_file, col_btn = st.columns([3, 1])
    
    with col_file:
        bank_file = st.file_uploader("ارفع كشف الحساب بصيغة PDF", type=["pdf"])
        
    with col_btn:
        st.write("##")
        st.markdown('<div class="search-btn-container">', unsafe_allow_html=True)
        search_clicked = st.button("🔍 بحث", key="search_bank_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    if bank_file is None:
        st.session_state.parsed_bank_df = None
        
    if bank_file is not None and search_clicked:
        all_rows = []
        try:
            with pdfplumber.open(bank_file) as pdf:
                total_pages = len(pdf.pages)
                
                # إظهار حز التحميل الأخضر الجميل
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, page in enumerate(pdf.pages):
                    percent_complete = int(((idx + 1) / total_pages) * 100)
                    progress_bar.progress(percent_complete)
                    status_text.markdown(f"<p style='color: #2e7d32; font-weight: bold;'>⏳ جاري معالجة الصفحة {idx + 1} من {total_pages}...</p>", unsafe_allow_html=True)
                    
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            # سحب أول 3 أعمدة فقط وتجاهل الباقي تماماً
                            if row and len(row) >= 3:
                                date_str = row[0]
                                if date_str and re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str.strip()):
                                    all_rows.append(row[:3])
                    time.sleep(0.1) # حركة انسيابية لحز التحميل الأخضر
                    
                progress_bar.empty()
                status_text.empty()
                
            df = pd.DataFrame(all_rows, columns=["İşlem Tarihi", "Açıklama", "Tutar"])
            df["Tutar_Clean"] = df["Tutar"].str.replace(" TL", "").str.replace(".", "").str.replace(",", ".").astype(float)
            df["İşlem Tarihi"] = pd.to_datetime(df["İşlem Tarihi"], format="%d.%m.%Y")
            
            df = df.sort_values(by="İşlem Tarihi", ascending=True).reset_index(drop=True)
            
            # تصنيف الحوالات بالاعتماد الكلي على نصوص البيان (Açıklama)
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
            df = df.sort_values(by="İşlem Tarihi", ascending=False).reset_index(drop=True)
            
            st.session_state.parsed_bank_df = df
            st.success("تم الانتهاء من سحب ومعالجة الحوالات بنجاح!")
            
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة الكشف. التفاصيل: {str(e)}")
            
    if st.session_state.parsed_bank_df is not None:
        df_bank = st.session_state.parsed_bank_df
        
        st.write("### 🔍 خيارات التصفية والبحث:")
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("من تاريخ", df_bank["İşlem Tarihi"].min().date(), key="b_start")
        with col2:
            end_date = st.date_input("إلى تاريخ", df_bank["İşlem Tarihi"].max().date(), key="b_end")
        with col3:
            op_type = st.selectbox("نوع الحوالة المطلوبة", ["الكل", "داخل", "خارج"], key="b_type")
            
        search_query = st.text_input("🔍 بحث باسم الشخص الحقيقي الذي حوّل", key="b_search")
        
        # تطبيق الفلترة
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
        
        # عرض الإحصائيات التفاعلية في بطاقة خضراء مريحة
        st.markdown(f"""
            <div style="background-color: #f1f8e9; padding: 15px; border-radius: 12px; border-right: 5px solid #4caf50; display: flex; justify-content: space-around; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); direction: rtl;">
                <div style="text-align: center; flex: 1;">
                    <span style="color: #555; font-size: 15px; font-weight: bold; display: block; margin-bottom: 5px;">📊 عدد الحركات (المفلترة)</span>
                    <span style="color: #2e7d32; font-size: 26px; font-weight: bold;">{total_count} حركة</span>
                </div>
                <div style="text-align: center; flex: 1; border-right: 2px solid #c8e6c9;">
                    <span style="color: #555; font-size: 15px; font-weight: bold; display: block; margin-bottom: 5px;">💰 إجمالي المبالغ للحوالات</span>
                    <span style="color: #2e7d32; font-size: 26px; font-weight: bold;">{total_sum:,.2f} TL</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # عرض البيانات كـ "بطاقات تفاعلية قابلة للتمدد" ممتازة لشاشات الهواتف
        st.write("### 📋 تفاصيل الحوالات (اضغط على أي بطاقة لعرض البيان البنكي كاملاً):")
        
        for idx, row in filtered_df.iterrows():
            card_title = f"📅 {row['İşlem Tarihi'].strftime('%Y-%m-%d')} | 👤 {row['اسم المحوّل']} | 🟢 {row['Tutar']}"
            with st.expander(card_title):
                st.markdown("<p style='font-weight: bold; color: #555; margin-bottom: 5px;'>📝 البيان البنكي المكتوب كامل في الـ PDF:</p>", unsafe_allow_html=True)
                st.text(row["Açıklama"])


# ==================== الصفحة الثانية: مطابقة ملفات التأمين ====================
elif st.session_state.active_tab == "insurance":
    st.markdown("<h2 style='text-align: right;'>مطابقة ملفات التأمين الثنائية</h2>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background-color: #e2f0fd; padding: 15px; border-radius: 8px; border-right: 5px solid #007bff; margin-bottom: 20px; text-align: right;">
            <h5 style="color: #004085; margin: 0; font-weight: bold;">⚠️ تنبيه وإرشادات قبل الرفع:</h5>
            <p style="color: #004085; margin: 8px 0 0 0;">
                يرجى التأكد من تنظيم ملفات الإكسل بحيث يحتوي <b>الملف الأول</b> و <b>الملف الثاني</b> على الترتيب التالي:<br>
                1. <b>العمود الأول (A):</b> نوع التأمين (مثال: تأمين سيارات).<br>
                2. <b>العمود الثاني (B):</b> رقم التأمين (مثال: 12345).<br>
                <i>ملاحظة: سيتم تلقائياً اعتبار السطر الأول كعنوان وسيتم استثناؤه من حسابات المقارنة.</i>
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        file1 = st.file_uploader("📂 ارفع ملف الإكسل: (الملف الأول)", type=["xlsx", "xls"], key="file1_up")
    with col_up2:
        file2 = st.file_uploader("📂 ارفع ملف الإكسل: (الملف الثاني)", type=["xlsx", "xls"], key="file2_up")
        
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
                
                # زر مقارنة التأمين البرتقالي الكبير والجميل
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
