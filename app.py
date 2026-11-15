from datetime import date
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from crop_rotation.pipeline import run,report,archive,source_archive,ROOT
from crop_rotation.data import geo_point

st.set_page_config(page_title='دورة | مستكشف الزراعة',page_icon='🌱',layout='wide')
st.markdown('''<style>@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');html,body,[class*="css"],.stApp{font-family:Tajawal,Arial,sans-serif} .stApp{background:#f6f8f2;color:#153d32} [data-testid="stMainBlockContainer"]{direction:rtl;padding-top:2rem} [data-testid="stSidebar"]{direction:rtl;background:#eaf0e4} h1,h2,h3{color:#174a39} [data-testid="stMetric"]{background:white;border:1px solid #dce5d6;border-radius:15px;padding:18px} .hero{background:#173f32;color:white;padding:28px 34px;border-radius:22px;margin-bottom:22px}.hero h1{color:white}.tag{color:#d3ddac;font-size:14px} [data-testid="stTabs"] button{font-size:17px} </style>''',unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="tag">دورة · قرار زراعي قابل للتفسير</div><h1>أرضك، موسمًا بعد موسم</h1><p>استكشف المناخ وقارن دورات زراعية وفق أولوياتك والأدلة المتاحة.</p></div>',unsafe_allow_html=True)
with st.sidebar:
    st.header('🌱 إعداد المزرعة')
    mode=st.radio('مصدر البيانات',['العينة الحقيقية المرفقة — دون اتصال','جلب مباشر من NASA POWER'])
    lat=st.number_input('خط العرض latitude',-90.,90.,32.55,format='%.5f');lon=st.number_input('خط الطول longitude',-180.,180.,35.85,format='%.5f')
    geo=st.file_uploader('نقطة أو مضلع GeoJSON',type=['geojson','json'])
    if geo:
        try: lat,lon=geo_point(json.load(geo));st.caption(f'نقطة ممثلة للمضلع، لا متوسط مكاني: {lat:.4f}, {lon:.4f}')
        except Exception as e: st.error(str(e));st.stop()
    start=st.date_input('من',date(2016,1,1));end=st.date_input('إلى',date(2025,12,31))
    names={'wheat':'قمح','barley':'شعير','lentil':'عدس','vetch':'بيقية'}
    current=st.selectbox('محصول الدورة الحالية المفترضة',list(names),format_func=names.get)
    sow=st.text_input('الزراعة MM-DD','11-01');harvest=st.text_input('الحصاد MM-DD','05-31')
    irrigation=st.selectbox('الري',['rainfed','supplemental','irrigated'],format_func=lambda x:{'rainfed':'بعلي مفترض','supplemental':'ري تكميلي','irrigated':'مروي'}[x])
    soil=st.selectbox('التربة/القيود',['unknown','loam','saline','waterlogged'],format_func=lambda x:{'unknown':'غير مقاسة','loam':'طميية — إدخال المستخدم','saline':'ملوحة تحتاج تحققًا','waterlogged':'صرف ضعيف'}[x])
    allowed=st.multiselect('المحاصيل المتاحة للمعدات والسوق',list(names),default=list(names),format_func=names.get)
    st.subheader('أولويات المقارنة')
    labels={'avoidance':'تجنب أيام الحر — مؤشر تعرض','diversity':'تنوع العائلات','cover':'مدة إشغال الأرض','fodder':'الاستخدام العلفي','income':'الدخل — الأدلة غير متاحة'}
    weights={k:st.slider(v,0,100,x) for (k,v),x in zip(labels.items(),[35,30,20,15,0])}
    with st.expander('عتبات المناخ'):
        heat=st.number_input('حر شديد ≥ °م',value=35.);frost=st.number_input('صقيع < °م',value=0.);rain=st.number_input('يوم ممطر ≥ مم',min_value=.01,value=1.);heavy=st.number_input('مطر شديد ≥ مم (عتبة مطلقة)',min_value=.1,value=20.)
    st.caption('جميع المواعيد والممارسات افتراضات قابلة للتعديل؛ لا تُنسب للموقع كوقائع.')
c={'latitude':lat,'longitude':lon,'start_date':str(start),'end_date':str(end),'current':current,'sow':sow,'harvest':harvest,'irrigation':irrigation,'soil':soil,'allowed':allowed,'heat':heat,'frost':frost,'rain':rain,'heavy':heavy}
@st.cache_data(show_spinner=False)
def compute(config,live,w): return run(config,live,w)
try:
    with st.spinner('تجهيز البيانات وحساب المؤشرات…'):t,a=compute(c,mode.startswith('جلب'),weights)
except Exception as e:
    st.error(f'تعذر التحليل: {e}');st.info('العينة المخزنة تخص 32.55، 35.85 فقط. لتغيير الموقع اختر الجلب المباشر. لا يجري استبدال فشل المصدر ببيانات اصطناعية.');st.stop()
st.info('حالة عرض ببيانات مناخية حقيقية • تربة وممارسات غير متحققة • دعم قرار استكشافي يحتاج مراجعة زراعية محلية')
d=t['daily'];annual=t['annual'];cols=st.columns(4)
for col,title,value in zip(cols,['الأيام في الفترة','اكتمال المطر','المطر السنوي المتوسط','ET₀ السنوي المتوسط'],[str(len(d)),f'{d.PRECTOTCORR.notna().mean():.1%}',f'{annual.loc[annual.full_period,"PRECTOTCORR_sum"].mean():.0f} مم',f'{annual.loc[annual.full_period,"ET0_sum"].mean():.0f} مم']):col.metric(title,value)
tabs=st.tabs(['نظرة على المناخ','مقارنة الدورات','التقويم والأدلة','جودة البيانات','التقرير والتنزيل'])
with tabs[0]:
    left,right=st.columns([2,1])
    with left:
        st.subheader('إيقاع المطر والحرارة')
        m=t['monthly'];fig=px.bar(m,x=m.index,y='PRECTOTCORR_sum',labels={'x':'الشهر','PRECTOTCORR_sum':'المطر مم'},color_discrete_sequence=['#4c8b71']);st.plotly_chart(fig,width='stretch')
        st.plotly_chart(px.line(m,x=m.index,y=['T2M_mean','T2M_MAX_mean','T2M_MIN_mean'],labels={'value':'°م','x':'الشهر'}),width='stretch')
    with right:
        st.subheader('نقطة الدراسة')
        st.map(pd.DataFrame({'latitude':[lat],'longitude':[lon]}),zoom=6)
        st.caption('خريطة الأساس تحتاج اتصالًا. POWER بيانات شبكية: أرصاد MERRA-2 نحو 0.5° × 0.625° وإشعاع نحو 1°؛ ليست قياسًا للحقل. المضلع يمثّل بنقطة داخلية فقط.')
    st.plotly_chart(px.line(m,x=m.index,y=['ET0_sum','P_minus_ET0_sum'],labels={'value':'مم','x':'الشهر'}),width='stretch')
    st.caption('ET₀ تبخر نتح سطح مرجعي. P−ET₀ مؤشر مناخي مبسط، وليس احتياج ري أو ميزانية تربة.')
    st.dataframe(t['extremes'],hide_index=True);st.dataframe(t['rain_sensitivity'],hide_index=True)
    st.write('موجة الحر: 3 أيام متتابعة على الأقل فوق العتبة؛ المفقود يقطع الحدث. الشذوذ نسبة إلى أشهر السجل المتاح نفسه، لا خط أساس مناخي 30 سنة.')
    st.plotly_chart(px.line(m,x=m.index,y='temperature_anomaly'),width='stretch');st.dataframe(t['trends'],hide_index=True)
with tabs[1]:
    st.subheader('ثلاثة مسارات، وأسباب واضحة')
    r=t['strategies']; cs=st.columns(3)
    for col,(_,row) in zip(cs,r.iterrows()):
        with col:
            st.markdown('### '+row.strategy);st.write(row.sequence)
            st.metric('درجة المفاضلة',f'{row.score:.1f} / 100' if pd.notna(row.score) else 'غير مرتبة')
            st.caption(f'تغطية الأدلة للأوزان المطلوبة: {row.weighted_evidence_coverage:.0%}')
            if row.blocks:st.error(row.blocks)
            st.write(f'أيام حر / دورة تاريخية كاملة: {row.hot_days:.1f}');st.write(f'أيام بلا محصول في التقويم: {row.bare_calendar_days:.0f}')
            st.write(row.warnings)
    st.caption('أفق مشترك: ثلاث سنوات. تواريخ العرض 2026–2029؛ التعرض محسوب بإعادة التقويم على دورات تاريخية كاملة، وليس توقعًا مناخيًا.')
    st.dataframe(r,hide_index=True)
    st.write('التطبيع: تجنب الحر min–max بين البدائل، التنوع (عدد العائلات−1)/2، الإشغال أيام التقويم/أيام الأفق، والعلف حصة المحاصيل ذات الاستخدام العلفي. مؤشرات منفصلة ولا تقيس إنتاجية أو صحة تربة فعلية. يُستبعد المعيار المفقود من الجميع وتُعاد معايرة الأوزان؛ كفاية الأدلة تظهر منفصلة.')
    st.subheader('هل يتغير الترتيب مع أولوياتك؟');st.dataframe(t['weight_sensitivity'],hide_index=True)
    if r.score.notna().sum()>1 and r.score.dropna().iloc[0]-r.score.dropna().iloc[1]<=5:st.warning('البدائل متقاربة بفارق لا يتجاوز 5 نقاط؛ لا يوجد فائز واضح.')
with tabs[2]:
    st.plotly_chart(px.timeline(t['calendar'],x_start='start',x_end='end',y='strategy',color='crop'),width='stretch')
    st.dataframe(t['calendar'],hide_index=True);st.dataframe(t['historical_cycles'],hide_index=True)
    st.subheader('سنوات جافة ورطبة وحارة من السجل');st.dataframe(t['stress_years'],hide_index=True);st.dataframe(t['stress_exposure'],hide_index=True)
    st.write('مدة إشغال الأرض لا تعني تغطية نباتية كاملة، والفترة خارج المحصول لا تعني غياب المخلفات. لا نحسب فقد تربة أو نيتروجين أو إنتاجية.')
    st.json(json.loads((ROOT/'crops.json').read_text()))
    st.subheader('ما يحتاج مراجعة محلية');st.write(' • '.join(a['local_review']))
with tabs[3]:
    st.dataframe(t['quality'],hide_index=True)
    st.write(f'تصحيح عامل الغيوم Rs/Rso: {int(d.radiation_adjusted.sum())} يومًا؛ حُفظت القيم الأصلية والمعدلة. لا استيفاء للفجوات. المجاميع غير المكتملة تظهر مفقودة مع مجموع الأيام المرصودة منفصلًا.')
    st.json(a)
    st.markdown((ROOT/'docs/sources.md').read_text())
    st.warning('SMAP وGPM وNDVI وECOSTRESS والتضاريس وGRACE غير مضافة؛ لا تُستنتج منها نتائج. لا يوجد نموذج إنتاجية أو تحقق زراعي ميداني.')
with tabs[4]:
    st.subheader('نتائج قابلة للمراجعة والمشاركة')
    st.download_button('تنزيل المشروع الكامل والكود ZIP',source_archive(),file_name='Crop_Rotation_Completed.zip',mime='application/zip')
    st.download_button('تنزيل التقرير العربي HTML',report(t,a).encode(),file_name='crop_rotation_report.html',mime='text/html')
    st.download_button('تنزيل جميع الجداول والافتراضات ZIP',archive(t,a),file_name='crop_rotation_results.zip',mime='application/zip')
    st.download_button('تنزيل البيانات اليومية CSV',d.to_csv().encode('utf-8-sig'),file_name='daily.csv',mime='text/csv')
    st.download_button('تنزيل جودة البيانات CSV',t['quality'].to_csv(index=False).encode('utf-8-sig'),file_name='quality.csv',mime='text/csv')
