import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from urllib.request import urlopen, Request
from urllib.parse import quote
import os

st.set_page_config(
    page_title="똑똑한 장보기 미션",
    page_icon="🛒",
    layout="wide",
)

# -----------------------------
# 기본 설정
# -----------------------------
MISSIONS = {
    "🍛 카레 만들기": 15000,
    "⛺ 여름캠핑 준비하기": 25000,
    "🎂 친구 생일파티 준비하기": 30000,
}

CSV_FILE = "products.csv"

# -----------------------------
# CSS
# -----------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        text-align: center;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .budget-box {
        padding: 15px 20px;
        border-radius: 15px;
        background: #f5f7ff;
        border: 1px solid #dfe4ff;
        margin-bottom: 20px;
    }
    .product-card {
        border: 1px solid #e5e5e5;
        border-radius: 15px;
        padding: 12px;
        background: white;
        margin-bottom: 10px;
    }
    .price {
        font-size: 1.15rem;
        font-weight: 700;
    }
    .cart-card {
        padding: 15px;
        border-radius: 15px;
        background: #fff8e8;
        border: 1px solid #ffe1a6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# CSV 읽기
# -----------------------------
@st.cache_data
def load_products():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=["품명", "가격", "이미지 url"])

    df = pd.read_csv(CSV_FILE)

    required = {"품명", "가격", "이미지 url"}
    missing = required - set(df.columns)
    if missing:
        st.error(
            f"products.csv에 다음 열이 필요합니다: {', '.join(sorted(missing))}"
        )
        st.stop()

    df = df.copy()
    df["가격"] = (
        df["가격"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("원", "", regex=False)
        .str.strip()
    )
    df["가격"] = pd.to_numeric(df["가격"], errors="coerce").fillna(0).astype(int)
    df["품명"] = df["품명"].astype(str)
    df["이미지 url"] = df["이미지 url"].fillna("").astype(str)
    return df.reset_index(drop=True)


products = load_products()

# -----------------------------
# 이미지 불러오기
# -----------------------------
@st.cache_data(show_spinner=False)
def get_image(url):
    if not url or url == "nan":
        return None
    try:
        req = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        data = urlopen(req, timeout=8).read()
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        return None


# -----------------------------
# 다운로드용 이미지 폰트
# -----------------------------
FONT_URL = (
    "https://github.com/google/fonts/raw/main/ofl/notosanskr/"
    "NotoSansKR%5Bwght%5D.ttf"
)

def find_korean_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansKR[wght].ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    local_font = os.path.join(".streamlit", "NotoSansKR.ttf")
    if os.path.exists(local_font):
        return local_font

    # Streamlit Cloud 등에 한글 폰트가 없을 경우 Noto Sans KR을 한 번 내려받음
    try:
        os.makedirs(".streamlit", exist_ok=True)
        req = Request(FONT_URL, headers={"User-Agent": "Mozilla/5.0"})
        data = urlopen(req, timeout=15).read()
        with open(local_font, "wb") as f:
            f.write(data)
        return local_font
    except Exception:
        return None


def load_font(size, bold=False):
    font_path = find_korean_font()
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    # 마지막 안전장치
    return ImageFont.load_default()


# -----------------------------
# 결과 그림 만들기
# -----------------------------
def make_result_image(mission, budget, cart, reasons):
    width = 1200
    padding = 55
    row_height = 180

    title_font = load_font(52, True)
    subtitle_font = load_font(30, True)
    body_font = load_font(25)
    small_font = load_font(21)

    total = sum(item["가격"] * item["수량"] for item in cart.values())
    remain = budget - total

    height = 230 + max(1, len(cart)) * row_height + 220
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    # 제목
    draw.text(
        (padding, 45),
        f"미션: {mission}",
        font=title_font,
        fill=(35, 35, 35),
    )
    draw.text(
        (padding, 120),
        f"예산 {budget:,}원  |  사용 {total:,}원  |  남은 돈 {remain:,}원",
        font=subtitle_font,
        fill=(60, 60, 60),
    )

    y = 205

    for item in cart.values():
        img = get_image(item["이미지 url"])

        # 상품 이미지
        box_w, box_h = 135, 135
        if img:
            img.thumbnail((box_w, box_h))
            x_img = padding
            y_img = y
            canvas.paste(
                img,
                (
                    x_img + (box_w - img.width) // 2,
                    y_img + (box_h - img.height) // 2,
                ),
            )

        x_text = 225
        draw.text(
            (x_text, y + 5),
            item["품명"],
            font=subtitle_font,
            fill=(25, 25, 25),
        )
        draw.text(
            (x_text, y + 55),
            f"{item['수량']}개 × {item['가격']:,}원 = "
            f"{item['수량'] * item['가격']:,}원",
            font=body_font,
            fill=(65, 65, 65),
        )

        reason = reasons.get(item["품명"], "").strip()
        if reason:
            # 너무 긴 문장은 이미지에서 잘리지 않도록 적당히 제한
            reason = reason[:70]
            draw.text(
                (x_text, y + 100),
                f"구매 이유: {reason}",
                font=small_font,
                fill=(90, 90, 90),
            )

        y += row_height

    # 하단
    draw.line(
        (padding, y + 5, width - padding, y + 5),
        fill=(220, 220, 220),
        width=2,
    )
    draw.text(
        (padding, y + 35),
        "나는 필요한 물건을 생각하고 예산에 맞게 장을 보았어요! 🛒",
        font=body_font,
        fill=(45, 45, 45),
    )

    output = BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()


# -----------------------------
# 세션 상태
# -----------------------------
defaults = {
    "page": "start",
    "mission": None,
    "budget": 0,
    "cart": {},
    "quantities": {},
    "reasons": {},
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def go_to_shopping(mission):
    st.session_state.mission = mission
    st.session_state.budget = MISSIONS[mission]
    st.session_state.cart = {}
    st.session_state.quantities = {}
    st.session_state.reasons = {}
    st.session_state.page = "shopping"


# -----------------------------
# 시작 화면
# -----------------------------
if st.session_state.page == "start":
    st.markdown('<div class="main-title">🛒 똑똑한 장보기 미션</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">예산을 생각하며 필요한 물건을 골라 보세요!</div>',
        unsafe_allow_html=True,
    )

    st.info("🎯 미션을 하나 골라 시작해 보세요.")

    cols = st.columns(3)

    for col, (mission, budget) in zip(cols, MISSIONS.items()):
        with col:
            st.markdown(f"### {mission}")
            st.markdown(f"**예산: {budget:,}원**")
            if st.button("이 미션 시작하기", key=f"start_{mission}", use_container_width=True):
                go_to_shopping(mission)
                st.rerun()


# -----------------------------
# 쇼핑 화면
# -----------------------------
elif st.session_state.page == "shopping":
    mission = st.session_state.mission
    budget = st.session_state.budget
    cart = st.session_state.cart

    st.markdown(f"# 🛒 {mission}")
    st.markdown(
        f"""
        <div class="budget-box">
        <b>💰 나의 예산</b> : {budget:,}원
        </div>
        """,
        unsafe_allow_html=True,
    )

    if products.empty:
        st.warning("products.csv에 상품을 넣어 주세요.")
        st.stop()

    st.subheader("🛍️ 상품을 골라 보세요")

    # 상품 카드
    cols_per_row = 4

    for start in range(0, len(products), cols_per_row):
        row = products.iloc[start:start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col, (idx, product) in zip(cols, row.iterrows()):
            name = product["품명"]
            price = int(product["가격"])
            url = product["이미지 url"]

            with col:
                img = get_image(url)
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.markdown(
                        "<div style='height:180px;display:flex;align-items:center;"
                        "justify-content:center;background:#f2f2f2;border-radius:10px;"
                        "font-size:50px;'>🛍️</div>",
                        unsafe_allow_html=True,
                    )

                st.markdown(f"**{name}**")
                st.markdown(f"<span class='price'>{price:,}원</span>", unsafe_allow_html=True)

                qty = st.number_input(
                    "수량",
                    min_value=0,
                    max_value=99,
                    value=int(st.session_state.quantities.get(idx, 0)),
                    step=1,
                    key=f"qty_{idx}",
                )
                st.session_state.quantities[idx] = qty

                if st.button(
                    "장바구니 담기",
                    key=f"add_{idx}",
                    use_container_width=True,
                ):
                    if qty > 0:
                        cart[name] = {
                            "품명": name,
                            "가격": price,
                            "이미지 url": url,
                            "수량": qty,
                        }
                        st.success(f"{name} {qty}개를 담았어요!")
                    else:
                        cart.pop(name, None)
                        st.warning("수량을 1개 이상 선택해 주세요.")

    st.divider()

    # 장바구니
    st.subheader("🧺 장바구니")

    if cart:
        total = 0

        for name in list(cart.keys()):
            item = cart[name]
            subtotal = item["가격"] * item["수량"]
            total += subtotal

            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            with c1:
                st.write(f"**{name}**")
            with c2:
                st.write(f"{item['수량']}개")
            with c3:
                st.write(f"{item['가격']:,}원")
            with c4:
                if st.button("삭제", key=f"delete_{name}"):
                    del cart[name]
                    st.rerun()

        remain = budget - total

        st.markdown(
            f"""
            <div class="cart-card">
            <b>총 사용 금액</b> : {total:,}원<br>
            <b>남은 돈</b> : {remain:,}원
            </div>
            """,
            unsafe_allow_html=True,
        )

        if total > budget:
            st.error(
                f"⚠️ 예산을 {total - budget:,}원 초과했어요. "
                "상품을 줄여서 예산 안에 맞춰 주세요!"
            )
        else:
            st.success("✅ 예산 안에서 잘 장보고 있어요!")

        submit_disabled = total > budget or total == 0

        if st.button(
            "📋 장보기 결과 제출하기",
            type="primary",
            use_container_width=True,
            disabled=submit_disabled,
        ):
            st.session_state.page = "result"
            st.rerun()

    else:
        st.info("아직 장바구니가 비어 있어요. 상품을 골라 담아 보세요!")
        st.button(
            "📋 장보기 결과 제출하기",
            type="primary",
            use_container_width=True,
            disabled=True,
        )


# -----------------------------
# 결과 화면
# -----------------------------
elif st.session_state.page == "result":
    mission = st.session_state.mission
    budget = st.session_state.budget
    cart = st.session_state.cart

    st.markdown(f"# 🎉 장보기 결과")
    st.markdown(f"## 미션: {mission}")

    total = sum(item["가격"] * item["수량"] for item in cart.values())
    remain = budget - total

    st.success(
        f"총 {total:,}원을 사용했고, **{remain:,}원**이 남았어요!"
    )

    st.subheader("🛍️ 내가 산 물건")

    for name, item in cart.items():
        c1, c2 = st.columns([1, 3])

        with c1:
            img = get_image(item["이미지 url"])
            if img:
                st.image(img, use_container_width=True)
            else:
                st.write("🛍️")

        with c2:
            st.markdown(f"### {item['품명']}")
            st.write(
                f"수량: **{item['수량']}개**  |  "
                f"개당 가격: **{item['가격']:,}원**  |  "
                f"합계: **{item['수량'] * item['가격']:,}원**"
            )

            reason = st.text_input(
                "왜 이 물건을 골랐나요?",
                value=st.session_state.reasons.get(name, ""),
                key=f"reason_{name}",
                placeholder="예: 카레를 만들 때 꼭 필요해서 골랐어요.",
            )
            st.session_state.reasons[name] = reason

        st.divider()

    all_reasons_written = all(
        st.session_state.reasons.get(name, "").strip()
        for name in cart.keys()
    )

    if all_reasons_written:
        st.success("🌟 모든 구매 이유를 작성했어요!")

        result_png = make_result_image(
            mission,
            budget,
            cart,
            st.session_state.reasons,
        )

        filename = "장보기_미션_결과.png"

        st.download_button(
            label="🖼️ 그림으로 저장하기",
            data=result_png,
            file_name=filename,
            mime="image/png",
            use_container_width=True,
        )

        st.caption(
            "PNG 이미지로 저장되며, 한글이 깨지지 않도록 한글 폰트를 우선 사용합니다."
        )
    else:
        st.info("✏️ 구매한 물건마다 구매 이유를 작성하면 그림으로 저장할 수 있어요.")

    st.divider()

    if st.button("🏠 처음으로 돌아가기", use_container_width=True):
        st.session_state.page = "start"
        st.session_state.mission = None
        st.session_state.budget = 0
        st.session_state.cart = {}
        st.session_state.quantities = {}
        st.session_state.reasons = {}
        st.rerun()
