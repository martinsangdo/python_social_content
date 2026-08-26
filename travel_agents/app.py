# %% [markdown]
# <h2>Multi-agent travel planner — Manager, Flight, Hotel, Activity and Budget agents backed by real APIs</h2>

import os
import sys
from datetime import datetime, timedelta

import streamlit as st

base_path = os.path.dirname(os.path.abspath(__file__))
if base_path not in sys.path:
    sys.path.insert(0, base_path)

from dotenv import load_dotenv
load_dotenv(override=True)

from agents import manager_agent

st.set_page_config(page_title="AI Travel Planner", page_icon="🧳", layout="wide")
st.title("🧳 AI Travel Planner — Multi-Agent")
st.caption(
    "Manager agent điều phối Flight / Hotel / Activity / Budget agent, "
    "tất cả dữ liệu lấy từ API thật — không dùng dữ liệu giả."
)

with st.expander("⚙️ Các API key cần trong .env (thư mục gốc dự án)"):
    st.markdown(
        """
- `GROQ_API_KEY` — manager agent dùng để trích xuất yêu cầu.
  Đăng ký miễn phí tại [console.groq.com/keys](https://console.groq.com/keys).
- `TRAVELPAYOUTS_TOKEN` — giá chuyến bay thật (Aviasales data).
  Đăng ký miễn phí, lấy token ngay tại [travelpayouts.com](https://www.travelpayouts.com/programs/100/tools/api).
- `RAPIDAPI_KEY` — giá khách sạn thật (Booking.com qua RapidAPI).
  Đăng ký tài khoản RapidAPI miễn phí tại [rapidapi.com](https://rapidapi.com), sau đó subscribe gói free
  của API [Booking.com (DataCrawler)](https://rapidapi.com/DataCrawler/api/booking-com15).
- Địa điểm/hoạt động thật lấy từ **OpenStreetMap (Overpass API)** — hoàn toàn miễn phí,
  không cần đăng ký hay API key.
"""
    )

if "trip" not in st.session_state:
    st.session_state.trip = {}
if "plan" not in st.session_state:
    st.session_state.plan = None

st.subheader("1. Mô tả chuyến đi của bạn")
user_text = st.text_area(
    "Yêu cầu chuyến đi",
    placeholder='Ví dụ: "Lên kế hoạch chuyến đi 3 ngày tới Barcelona vào tuần tới, '
                'khởi hành từ Hà Nội, cho 2 người."',
    height=90,
    label_visibility="collapsed",
)

analyze_clicked = st.button("🔍 Phân tích yêu cầu", type="primary")

if analyze_clicked:
    if not user_text.strip():
        st.warning("Vui lòng nhập yêu cầu chuyến đi.")
    else:
        with st.spinner("Manager agent đang trích xuất thông tin..."):
            try:
                extracted = manager_agent.extract_trip_request(user_text, known=st.session_state.trip)
                st.session_state.trip = extracted
                st.session_state.plan = None
            except Exception as exc:
                st.error(f"Không thể trích xuất yêu cầu: {exc}")

trip = st.session_state.trip
if trip:
    st.subheader("2. Xác nhận thông tin chuyến đi")
    if trip.get("missing"):
        st.warning(
            "Thiếu thông tin: " + ", ".join(trip["missing"]) +
            ". Vui lòng điền vào bên dưới trước khi lập kế hoạch."
        )

    c1, c2 = st.columns(2)
    with c1:
        origin_city = st.text_input("Điểm khởi hành", value=trip.get("origin_city") or "")
        destination_city = st.text_input("Điểm đến", value=trip.get("destination_city") or "")
    with c2:
        try:
            default_date = (
                datetime.strptime(trip["start_date"], "%Y-%m-%d").date()
                if trip.get("start_date") else datetime.now().date() + timedelta(days=7)
            )
        except ValueError:
            default_date = datetime.now().date() + timedelta(days=7)
        start_date = st.date_input("Ngày khởi hành", value=default_date)
        duration_days = st.number_input(
            "Số ngày", min_value=1, max_value=30, value=int(trip.get("duration_days") or 3)
        )

    travelers = st.number_input(
        "Số khách du lịch", min_value=1, max_value=20, value=int(trip.get("travelers") or 1)
    )

    plan_clicked = st.button("🧭 Lập kế hoạch chuyến đi", type="primary")

    if plan_clicked:
        missing_now = []
        if not origin_city.strip():
            missing_now.append("điểm khởi hành")
        if not destination_city.strip():
            missing_now.append("điểm đến")
        if missing_now:
            st.error("Vui lòng điền: " + ", ".join(missing_now))
        else:
            confirmed_trip = {
                "origin_city": origin_city.strip(),
                "destination_city": destination_city.strip(),
                "start_date": start_date.strftime("%Y-%m-%d"),
                "duration_days": int(duration_days),
                "travelers": int(travelers),
            }
            st.session_state.trip = confirmed_trip
            with st.spinner("Flight / Hotel / Activity / Budget agent đang gọi API thật..."):
                try:
                    st.session_state.plan = manager_agent.plan_trip(confirmed_trip)
                except Exception as exc:
                    st.error(f"Lập kế hoạch thất bại: {exc}")
                    st.session_state.plan = None

plan = st.session_state.plan
if plan:
    st.subheader("3. Kế hoạch chuyến đi")

    for err in plan["errors"]:
        st.error(err)

    req = plan["request"]
    st.markdown(
        f"**{req['origin_city']} → {req['destination_city']}** | "
        f"{req['start_date']} → {plan['return_date']} ({req['duration_days']} ngày) | "
        f"{req['travelers']} khách"
    )

    tab_flights, tab_hotels, tab_activities, tab_budget = st.tabs(
        ["✈️ Chuyến bay", "🏨 Khách sạn", "📍 Hoạt động", "💰 Ngân sách"]
    )

    with tab_flights:
        flights = plan.get("flights")
        if flights and (flights["outbound_offers"] or flights["inbound_offers"]):
            st.caption(f"{flights['origin_airport']} → {flights['destination_airport']}")
            st.caption(
                "Giá thực tế người dùng Aviasales đã tìm thấy gần đây cho tuyến này "
                "(không phải báo giá đặt vé trực tiếp). Giá là cho 1 khách/chặng."
            )

            def _render_leg(title, offers, exact_date):
                st.markdown(f"**{title}**")
                if not exact_date and offers:
                    st.caption(
                        "Không có dữ liệu đúng ngày yêu cầu — hiển thị giá rẻ nhất "
                        "tìm được trong cả tháng đó."
                    )
                if not offers:
                    st.info("Không có dữ liệu chuyến bay thật cho chặng này.")
                    return
                for offer in offers[:5]:
                    with st.container(border=True):
                        st.markdown(f"**{offer['price']:.2f} {offer['currency']} / khách**")
                        stops_txt = (
                            "bay thẳng" if not offer.get("transfers")
                            else f"{offer['transfers']} điểm dừng"
                        )
                        st.write(
                            f"Hãng {offer.get('airline') or '?'} {offer.get('flight_number') or ''} · "
                            f"khởi hành {offer.get('departure_at') or '?'} · {stops_txt}"
                        )
                        if offer.get("link"):
                            st.caption(offer["link"])

            _render_leg("Chiều đi", flights["outbound_offers"], flights["outbound_exact_date"])
            if flights["return_requested"]:
                st.divider()
                _render_leg("Chiều về", flights["inbound_offers"], flights["inbound_exact_date"])
        else:
            st.info("Không có dữ liệu chuyến bay thật từ Aviasales/Travelpayouts cho tuyến này.")

    with tab_hotels:
        hotels = plan.get("hotels")
        if hotels and hotels["offers"]:
            for offer in hotels["offers"]:
                with st.container(border=True):
                    st.markdown(f"**{offer['hotel_name']}**")
                    st.write(
                        f"{offer['total_price']:.2f} {offer['currency']} "
                        f"({offer['check_in']} → {offer['check_out']})"
                    )
        else:
            st.info("Không có dữ liệu khách sạn thật từ Booking.com (RapidAPI) cho thành phố này.")

    with tab_activities:
        activities = plan.get("activities")
        if activities:
            for act in activities:
                with st.container(border=True):
                    st.markdown(f"**{act['name']}**")
                    st.caption(f"{act['kinds']} · cách trung tâm {act['distance_m']} m")
                    if act.get("description"):
                        st.write(act["description"][:400])
        else:
            st.info("Không có dữ liệu địa điểm thật từ OpenStreetMap (Overpass) cho khu vực này.")

    with tab_budget:
        budget = plan.get("budget")
        if budget:
            for item in budget["breakdown"]:
                if item["amount"] is not None:
                    st.write(f"- {item['item']}: **{item['amount']} {item['currency']}**")
                else:
                    st.write(f"- {item['item']}: _không có dữ liệu_")
            if budget["complete"]:
                st.success(f"Tổng cộng: **{budget['total']:.2f} {budget['currency']}**")
            else:
                st.warning(
                    f"Tổng cộng (một phần, thiếu dữ liệu): "
                    f"**{budget['total']:.2f} {budget['currency'] or ''}**"
                )
            st.caption(budget["note"])
