import os
import html
from io import BytesIO
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title='똑똑한 장보기 미션', page_icon='🛒', layout='wide')

MISSIONS = {
    '🍛 카레 만들기': 15000,
    '🏕️ 여름캠핑 준비하기': 25000,
    '🎂 친구 생일파티 준비하기': 30000,
}
CSV_FILE = 'products.csv'
FONT_FILE = 'NanumHumanRegular.ttf'

st.markdown('''
<style>
.block-container{max-width:1200px;padding-top:2rem;padding-bottom:3rem}
.main-title{text-align:center;font-size:2.5rem;font-weight:900;margin-bottom:.4rem}
.sub-title{text-align:center;color:#666;margin-bottom:2rem}
.mission-card{height:225px;border:1px solid #e5e7eb;border-radius:20px;padding:25px 20px;text-align:center;background:#fff;box-shadow:0 3px 12px rgba(0,0,0,.06);box-sizing:border-box}
.mission-icon{font-size:3.2rem;margin-bottom:8px}.mission-name{height:55px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:800}.mission-budget{margin-top:10px;color:#555}
.product-card{height:385px;border:1px solid #e4e7eb;border-radius:18px;background:#fff;padding:16px;box-sizing:border-box;box-shadow:0 3px 12px rgba(0,0,0,.055);overflow:hidden}
.product-image-wrap{height:245px;width:100%;display:flex;align-items:center;justify-content:center;background:#f7f7f7;border-radius:12px;overflow:hidden;margin-bottom:14px}
.product-image{width:100%;height:100%;object-fit:contain;display:block}.product-name{height:38px;font-size:1.08rem;font-weight:800;display:flex;align-items:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.product-price{height:30px;font-size:1.08rem;font-weight:800;display:flex;align-items:center}
.cart-box{border:1px solid #f0d99a;border-radius:18px;padding:18px;background:#fffaf0}.cart-item{min-height:88px;display:flex;align-items:center;gap:14px;padding:9px 0;border-bottom:1px solid #eadfca}.cart-item:last-child{border-bottom:0}.cart-img{width:70px;height:70px;object-fit:contain;border-radius:10px;background:#fff;border:1px solid #eee;flex-shrink:0}.cart-info{min-width:0}.cart-name{font-weight:800;margin-bottom:4px}.cart-price{color:#555;font-size:.9rem}
.summary-box{border-radius:15px;padding:17px 20px;background:#f5f7ff;border:1px solid #dfe4ff;margin:15px 0;line-height:1.9}.result-title{text-align:center;font-size:2.6rem;font-weight:900;margin:5px 0 28px}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load_products():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=['품명','가격','이미지 url'])
    df = pd.read_csv(CSV_FILE)
    required = {'품명','가격','이미지 url'}
    missing = required - set(df.columns)
    if missing:
        st.error('products.csv에 필요한 열이 없습니다: ' + ', '.join(sorted(missing)))
        st.stop()
    df['가격'] = pd.to_numeric(df['가격'].astype(str).str.replace(',','',regex=False).str.replace('원','',regex=False), errors='coerce').fillna(0).astype(int)
    df['품명'] = df['품명'].astype(str)
    df['이미지 url'] = df['이미지 url'].fillna('').astype(str)
    return df.reset_index(drop=True)

products = load_products()

def esc(v):
    return html.escape(str(v), quote=True)

def product_card(name, price, url):
    name_e, url_e = esc(name), esc(url)
    img = f'<img class="product-image" src="{url_e}" alt="{name_e}" loading="lazy">' if url else '<div style="font-size:55px">🛍️</div>'
    return f'''<div class="product-card"><div class="product-image-wrap">{img}</div><div class="product-name" title="{name_e}">{name_e}</div><div class="product-price">{price:,}원</div></div>'''

def cart_markup(cart):
    out=[]
    for item in cart.values():
        n,u=esc(item['품명']),esc(item['이미지 url']); sub=item['가격']*item['수량']
        img=f'<img class="cart-img" src="{u}" alt="{n}" loading="lazy">' if u else '<div class="cart-img" style="display:flex;align-items:center;justify-content:center">🛍️</div>'
        out.append(f'<div class="cart-item">{img}<div class="cart-info"><div class="cart-name">{n}</div><div class="cart-price">{item["수량"]}개 × {item["가격"]:,}원 = <b>{sub:,}원</b></div></div></div>')
    return ''.join(out)

def get_font(size):
    candidates=[FONT_FILE,'./NanumHumanRegular.ttf','/usr/share/fonts/truetype/nanum/NanumGothic.ttf','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for p in candidates:
        if os.path.exists(p):
            try:return ImageFont.truetype(p,size)
            except Exception:pass
    return ImageFont.load_default()

def fetch_image(url):
    if not url:return None
    try:
        req=Request(url,headers={'User-Agent':'Mozilla/5.0'})
        return Image.open(BytesIO(urlopen(req,timeout=6).read())).convert('RGB')
    except Exception:return None

def make_png(mission,budget,cart,reasons):
    W=1400; pad=70; row=175
    title=get_font(58); section=get_font(34); body=get_font(27); small=get_font(23)
    total=sum(x['가격']*x['수량'] for x in cart.values()); balance=budget-total
    H=430+len(cart)*row+260+max(1,len(cart))*55
    canvas=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(canvas)
    t=f'미션: {mission}'; box=d.textbbox((0,0),t,font=title); d.text(((W-(box[2]-box[0]))/2,45),t,font=title,fill=(30,30,30))
    y=145; d.text((pad,y),'구매 품목',font=section,fill=(30,30,30)); y+=60
    for label,x in [('상품',250),('수량',720),('단가',850),('합계',1060)]:d.text((x,y),label,font=small,fill=(80,80,80))
    y+=45; d.line((pad,y,W-pad,y),fill=(210,210,210),width=2); y+=15
    for item in cart.values():
        im=fetch_image(item['이미지 url'])
        if im:
            im.thumbnail((125,125)); canvas.paste(im,(75+(125-im.width)//2,y+(125-im.height)//2))
        d.text((250,y+30),str(item['품명']),font=body,fill=(30,30,30)); d.text((720,y+30),f"{item['수량']}개",font=body,fill=(30,30,30)); d.text((850,y+30),f"{item['가격']:,}원",font=body,fill=(30,30,30)); d.text((1060,y+30),f"{item['가격']*item['수량']:,}원",font=body,fill=(30,30,30))
        y+=row; d.line((pad,y-10,W-pad,y-10),fill=(235,235,235),width=1)
    y+=20; d.text((pad,y),'금액 정보',font=section,fill=(30,30,30)); y+=60
    d.text((pad,y),f'주어진 금액: {budget:,}원',font=body,fill=(30,30,30)); d.text((500,y),f'총 사용 금액: {total:,}원',font=body,fill=(30,30,30)); d.text((1000,y),f'잔액: {balance:,}원',font=body,fill=(30,30,30))
    y+=95; d.text((pad,y),'구매 이유',font=section,fill=(30,30,30)); y+=60
    for item in cart.values():
        reason=reasons.get(item['품명'],'').strip().replace('\n',' ')
        if len(reason)>65:reason=reason[:65]+'...'
        d.text((pad+10,y),f"• {item['품명']}: {reason}",font=small,fill=(55,55,55)); y+=55
    b=BytesIO(); canvas.save(b,format='PNG'); return b.getvalue()

# session state
for k,v in {'page':'start','mission':None,'budget':0,'cart':{},'quantities':{},'reasons':{},'reasons_submitted':False}.items():
    if k not in st.session_state:st.session_state[k]=v

def start(mission):
    st.session_state.update(page='shopping',mission=mission,budget=MISSIONS[mission],cart={},quantities={},reasons={},reasons_submitted=False)

# START
if st.session_state.page=='start':
    st.markdown('<div class="main-title">🛒 똑똑한 장보기 미션</div>',unsafe_allow_html=True)
    st.markdown('<div class="sub-title">예산을 생각하며 필요한 물건을 골라 보세요!</div>',unsafe_allow_html=True)
    cols=st.columns(3)
    for col,(mission,budget) in zip(cols,MISSIONS.items()):
        icon,name=mission.split(maxsplit=1)
        with col:
            st.markdown(f'<div class="mission-card"><div class="mission-icon">{icon}</div><div class="mission-name">{esc(name)}</div><div class="mission-budget">예산 <b>{budget:,}원</b></div></div>',unsafe_allow_html=True)
            if st.button('이 미션 시작하기',key='start_'+mission,use_container_width=True,type='primary'):start(mission);st.rerun()

# SHOPPING
elif st.session_state.page=='shopping':
    mission=st.session_state.mission; budget=st.session_state.budget; cart=st.session_state.cart
    st.markdown(f'# 🛍️ {esc(mission)}',unsafe_allow_html=True)
    st.markdown(f'<div class="summary-box"><b>주어진 예산</b> : {budget:,}원</div>',unsafe_allow_html=True)
    st.subheader('상품을 골라 보세요')
    if products.empty:st.warning('products.csv에 상품을 넣어 주세요.');st.stop()

    for start_idx in range(0,len(products),3):
        row=products.iloc[start_idx:start_idx+3]; cols=st.columns(3)
        for col,(idx,p) in zip(cols,row.iterrows()):
            name,price,url=p['품명'],int(p['가격']),p['이미지 url']
            with col:
                st.markdown(product_card(name,price,url),unsafe_allow_html=True)
                q=int(st.session_state.quantities.get(idx,0)); a,b,c=st.columns([1,1.3,1])
                with a:
                    if st.button('−',key=f'minus_{idx}',use_container_width=True):st.session_state.quantities[idx]=max(0,q-1);st.rerun()
                with b:st.markdown(f'<div style="text-align:center;padding-top:8px;font-weight:800">{q}개</div>',unsafe_allow_html=True)
                with c:
                    if st.button('+',key=f'plus_{idx}',use_container_width=True):st.session_state.quantities[idx]=min(99,q+1);st.rerun()
                if st.button('🧺 장바구니 담기',key=f'add_{idx}',use_container_width=True):
                    if q>0:cart[name]={'품명':name,'가격':price,'이미지 url':url,'수량':q};st.success(f'{name} {q}개를 담았어요!')
                    else:cart.pop(name,None);st.warning('수량을 1개 이상 선택해 주세요.')
        st.markdown('<div style="height:15px"></div>',unsafe_allow_html=True)

    st.divider();st.subheader('🧺 장바구니')
    if cart:
        total=sum(x['가격']*x['수량'] for x in cart.values()); balance=budget-total
        st.markdown(f'<div class="cart-box">{cart_markup(cart)}</div>',unsafe_allow_html=True)
        st.markdown('#### 장바구니 수량 조절')
        for name,item in list(cart.items()):
            c1,c2,c3,c4=st.columns([4,1,1,1])
            with c1:st.write(f'**{name}**')
            with c2:
                if st.button('−',key='cm_'+name,use_container_width=True):cart[name]['수량']-=1; cart.pop(name,None) if cart[name]['수량']<=0 else None; st.rerun()
            with c3:st.markdown(f'<div style="text-align:center;padding-top:8px;font-weight:800">{item["수량"]}개</div>',unsafe_allow_html=True)
            with c4:
                if st.button('+',key='cp_'+name,use_container_width=True):cart[name]['수량']=min(99,cart[name]['수량']+1);st.rerun()
        st.markdown(f'<div class="summary-box"><b>총 사용 금액</b> : {total:,}원<br><b>잔액</b> : {balance:,}원</div>',unsafe_allow_html=True)
        if total>budget:st.error(f'⚠️ 예산을 {total-budget:,}원 초과했어요! 상품을 줄여 주세요.')
        elif total==0:st.warning('상품을 한 개 이상 담아 주세요.')
        else:st.success(f'✅ 예산 안에서 잘 장보고 있어요. {balance:,}원이 남아요!')
        if st.button('📋 장바구니 제출하기',type='primary',use_container_width=True,disabled=(total>budget or total==0)):
            st.session_state.page='result';st.session_state.reasons_submitted=False;st.rerun()
    else:
        st.info('아직 장바구니가 비어 있어요. 상품을 골라 담아 보세요!')
        st.button('📋 장바구니 제출하기',type='primary',use_container_width=True,disabled=True)

# RESULT
else:
    mission=st.session_state.mission;budget=st.session_state.budget;cart=st.session_state.cart
    total=sum(x['가격']*x['수량'] for x in cart.values());balance=budget-total
    st.markdown(f'<div class="result-title">미션: {esc(mission)}</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="summary-box" style="text-align:center"><b>주어진 금액</b> {budget:,}원 &nbsp; | &nbsp; <b>총 사용 금액</b> {total:,}원 &nbsp; | &nbsp; <b>잔액</b> {balance:,}원</div>',unsafe_allow_html=True)
    st.subheader('구매 품목')
    h=st.columns([1.2,3,1,1.5,1.7])
    for c,t in zip(h,['이미지','이름','수량','단가','합계']):c.markdown(f'**{t}**')
    for name,item in cart.items():
        c1,c2,c3,c4,c5=st.columns([1.2,3,1,1.5,1.7]);url=esc(item['이미지 url'])
        with c1:
            if url:st.markdown(f'<img src="{url}" style="width:90px;height:90px;object-fit:contain;border-radius:12px;background:#f7f7f7;border:1px solid #eee">',unsafe_allow_html=True)
            else:st.write('🛍️')
        with c2:st.write(f'**{name}**')
        with c3:st.write(f'{item["수량"]}개')
        with c4:st.write(f'{item["가격"]:,}원')
        with c5:st.write(f'**{item["가격"]*item["수량"]:,}원**')
        reason=st.text_area(f'{name}의 구매 이유',value=st.session_state.reasons.get(name,''),key='reason_'+name,placeholder='왜 이 물건을 골랐나요?')
        st.session_state.reasons[name]=reason
        st.divider()
    complete=all(st.session_state.reasons.get(n,'').strip() for n in cart)
    if complete:
        if st.button('✏️ 구매 이유 제출하기',type='primary',use_container_width=True):st.session_state.reasons_submitted=True;st.rerun()
    else:st.info('모든 구매 품목의 구매 이유를 작성해 주세요.')
    if st.session_state.reasons_submitted:
        png=make_png(mission,budget,cart,st.session_state.reasons)
        st.success('🎨 결과 그림을 만들었어요!')
        st.download_button('🖼️ PNG로 다운',data=png,file_name='장보기_미션_결과.png',mime='image/png',use_container_width=True)
        if not os.path.exists(FONT_FILE):st.caption('한글이 깨지지 않도록 NanumHumanRegular.ttf를 프로젝트 폴더에 추가해 주세요.')
    st.markdown('<br>',unsafe_allow_html=True)
    if st.button('🏠 처음으로 돌아가기',use_container_width=True):
        st.session_state.update(page='start',mission=None,budget=0,cart={},quantities={},reasons={},reasons_submitted=False);st.rerun()
