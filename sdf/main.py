
from datetime import date, datetime, time

import pandas as pd
import plotly.express as px
import streamlit as st

from database import Database
from models import Event
from services import (
    AuthService,
    EventService,
    RegistrationService,
)
from validators import ValidationError


st.set_page_config(
    page_title="Universitet Tədbirləri",
    page_icon="🎓",
    layout="wide",
)


def show_error(error):
    st.error(str(error))

def initialize_app():
    try:
        Database.initialize()
        st.success("Neon verilənlər bazasına bağlantı uğurludur!")
        return True

    except Exception as exc:
        st.error(f"Xəta növü: {type(exc).__name__}")
        st.error(f"Xəta detalları: {exc}")
        return False




def login_page():
    st.title("🎓 Universitet Tədbirlərinin İdarə Edilməsi")
    login_tab, register_tab = st.tabs(["Daxil ol", "Qeydiyyat"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("E-poçt", key="login_email")
            password = st.text_input(
                "Şifrə", type="password", key="login_password"
            )
            submitted = st.form_submit_button(
                "Daxil ol", use_container_width=True
            )

        if submitted:
            try:
                user = AuthService.login(email, password)
                st.session_state["user"] = {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                }
                st.rerun()
            except (ValidationError, ValueError) as exc:
                show_error(exc)
            except Exception:
                st.error("Giriş zamanı xəta baş verdi.")

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Ad və soyad")
            email = st.text_input("E-poçt", key="register_email")
            password = st.text_input(
                "Şifrə (ən azı 8 simvol)", type="password"
            )
            submitted = st.form_submit_button(
                "Qeydiyyatdan keç", use_container_width=True
            )

        if submitted:
            try:
                AuthService.register(full_name, email, password)
                st.success(
                    "Qeydiyyat uğurludur. İndi sistemə daxil ola bilərsiniz."
                )
            except (ValidationError, ValueError) as exc:
                show_error(exc)
            except Exception:
                st.error(
                    "Qeydiyyat zamanı xəta baş verdi. "
                    "Məlumatları yoxlayın."
                )


def event_filters(categories):
    with st.expander("🔎 Tədbirləri axtar və filtrlə", expanded=True):
        col1, col2, col3 = st.columns(3)

        search = col1.text_input("Tədbirin adı")
        category_options = {
            "Bütün kateqoriyalar": None,
            **{item["name"]: item["id"] for item in categories},
        }
        selected_category = col2.selectbox(
            "Kateqoriya", list(category_options.keys())
        )
        location = col3.text_input("Keçirilmə yeri")

        use_dates = st.checkbox("Tarix aralığı tətbiq et")
        start_date, end_date = None, None

        if use_dates:
            date_col1, date_col2 = st.columns(2)
            start_date = date_col1.date_input(
                "Başlanğıc tarixi", value=date.today()
            )
            end_date = date_col2.date_input(
                "Son tarix", value=date.today()
            )

            if start_date > end_date:
                st.warning("Başlanğıc tarixi son tarixdən sonra ola bilməz.")
                return None

        return {
            "search": search,
            "category_id": category_options[selected_category],
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
        }


def events_page(user):
    st.subheader("📅 Tədbirlər")

    categories = EventService.categories()
    filters = event_filters(categories)

    if filters is None:
        return

    try:
        events = EventService.list_events(**filters)
    except Exception:
        st.error("Tədbirləri yükləmək mümkün olmadı.")
        return

    if not events:
        st.info("Axtarışınıza uyğun tədbir tapılmadı.")
        return

    today = date.today()

    for event in events:
        event_date = event["event_date"]
        is_past = event_date < today
        status = "Keçmiş tədbir" if is_past else (
            "Bu gün" if event_date == today else "Gələcək tədbir"
        )

        with st.container(border=True):
            left, right = st.columns([4, 1])

            left.markdown(f"### {event['title']}")
            left.caption(
                f"{event['category']} · {status} · "
                f"{event_date:%d.%m.%Y} · "
                f"{event['event_time']:%H:%M}"
            )
            left.write(event["description"])
            left.write(f"📍 {event['location']}")
            left.progress(
                min(
                    event["registered_count"] / event["max_participants"],
                    1.0,
                ),
                text=(
                    f"{event['registered_count']} / "
                    f"{event['max_participants']} iştirakçı"
                ),
            )

            if user["role"] == "participant":
                if is_past:
                    right.caption("Qeydiyyat bağlıdır")
                else:
                    if right.button(
                        "Qeydiyyatdan keç",
                        key=f"register_{event['id']}",
                        disabled=(
                            event["registered_count"]
                            >= event["max_participants"]
                        ),
                    ):
                        try:
                            RegistrationService.register(
                                user["id"], event["id"]
                            )
                            st.success("Qeydiyyat uğurla tamamlandı.")
                            st.rerun()
                        except ValidationError as exc:
                            show_error(exc)
                        except Exception:
                            st.error("Qeydiyyat zamanı xəta baş verdi.")


def my_registrations_page(user):
    st.subheader("📝 Mənim qeydiyyatlarım")

    try:
        registrations = RegistrationService.my_events(user["id"])
    except Exception:
        st.error("Qeydiyyatları yükləmək mümkün olmadı.")
        return

    if not registrations:
        st.info("Hələ heç bir tədbirə qeydiyyatdan keçməmisiniz.")
        return

    for item in registrations:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{item['title']}**")
            col1.write(
                f"{item['event_date']:%d.%m.%Y} · "
                f"{item['event_time']:%H:%M} · {item['location']}"
            )

            if col2.button("Ləğv et", key=f"cancel_{item['id']}"):
                try:
                    cancelled = RegistrationService.cancel(
                        user["id"], item["id"]
                    )
                    if cancelled:
                        st.success("Qeydiyyat ləğv edildi.")
                    else:
                        st.warning("Qeydiyyat artıq mövcud deyil.")
                    st.rerun()
                except Exception:
                    st.error("Qeydiyyatı ləğv etmək mümkün olmadı.")


def statistics_page():
    st.subheader("📊 İdarəetmə paneli")

    try:
        summary, popular, categories = EventService.statistics()
    except Exception:
        st.error("Statistikanı yükləmək mümkün olmadı.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Ümumi tədbirlər", summary["total_events"])
    col2.metric("Ümumi qeydiyyatlar", summary["total_registrations"])
    col3.metric("İştirakçılar", summary["total_users"])

    st.markdown("#### Ən çox qeydiyyat olan tədbirlər")
    if popular:
        popular_df = pd.DataFrame(popular)
        st.bar_chart(
            popular_df,
            x="title",
            y="registrations",
            horizontal=True,
        )

    st.markdown("#### Kateqoriyalara görə tədbirlər")
    if categories:
        category_df = pd.DataFrame(categories)
        category_df = category_df[category_df["total"] > 0]

        if not category_df.empty:
            fig = px.pie(
                category_df,
                names="category",
                values="total",
                title="Tədbirlərin kateqoriyalar üzrə bölgüsü",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Statistika üçün hələ tədbir yoxdur.")


def event_form(categories, event=None):
    """Tədbir yaratmaq və redaktə etmək üçün ortaq forma."""
    editing = event is not None
    category_ids = [item["id"] for item in categories]

    with st.form("edit_event_form" if editing else "create_event_form"):
        title = st.text_input(
            "Tədbirin adı", value=event["title"] if editing else ""
        )
        description = st.text_area(
            "Təsvir", value=event["description"] if editing else ""
        )

        default_category = (
            category_ids.index(event["category_id"])
            if editing and event["category_id"] in category_ids
            else 0
        )
        category_index = st.selectbox(
            "Kateqoriya",
            range(len(categories)),
            index=default_category,
            format_func=lambda index: categories[index]["name"],
        )

        event_date = st.date_input(
            "Tarix",
            value=event["event_date"] if editing else date.today(),
        )
        event_time = st.time_input(
            "Saat",
            value=event["event_time"] if editing else time(10, 0),
        )
        location = st.text_input(
            "Keçirilmə yeri",
            value=event["location"] if editing else "",
        )
        capacity = st.number_input(
            "Maksimum iştirakçı sayı",
            min_value=1,
            max_value=100000,
            value=(
                event["max_participants"] if editing else 50
            ),
            step=1,
        )

        submitted = st.form_submit_button(
            "Dəyişiklikləri yadda saxla" if editing else "Tədbir yarat"
        )

    if submitted:
        try:
            new_event = Event(
                title=title,
                description=description,
                category_id=categories[category_index]["id"],
                event_date=event_date,
                event_time=event_time,
                location=location,
                max_participants=int(capacity),
            )

            if editing:
                EventService.update(event["id"], new_event)
                st.success("Tədbir yeniləndi.")
            else:
                EventService.create(
                    new_event, st.session_state["user"]["id"]
                )
                st.success("Tədbir yaradıldı.")

            st.rerun()
        except ValidationError as exc:
            show_error(exc)
        except Exception:
            st.error(
                "Tədbiri yadda saxlamaq mümkün olmadı. "
                "Kateqoriya və verilənlər bazası əlaqəsini yoxlayın."
            )


def admin_page():
    st.subheader("⚙️ Tədbirlərin idarə edilməsi")
    categories = EventService.categories()

    create_tab, edit_tab, delete_tab = st.tabs(
        ["Yeni tədbir", "Redaktə et", "Sil"]
    )

    with create_tab:
        event_form(categories)

    try:
        all_events = EventService.list_events()
    except Exception:
        st.error("Tədbirləri yükləmək mümkün olmadı.")
        return

    if not all_events:
        st.info("Hələ tədbir yaradılmayıb.")
        return

    event_options = {
        f"{item['title']} (ID: {item['id']})": item
        for item in all_events
    }

    with edit_tab:
        selected_label = st.selectbox(
            "Redaktə ediləcək tədbir",
            list(event_options.keys()),
            key="edit_event_select",
        )
        event_form(categories, event_options[selected_label])

    with delete_tab:
        selected_label = st.selectbox(
            "Silinəcək tədbir",
            list(event_options.keys()),
            key="delete_event_select",
        )
        selected_event = event_options[selected_label]

        st.warning(
            "Tədbirin silinməsi ona aid qeydiyyatları da siləcək."
        )
        confirm = st.checkbox(
            "Silmək istədiyimi təsdiq edirəm",
            key="confirm_delete",
        )

        if st.button("Tədbiri sil", disabled=not confirm):
            try:
                EventService.delete(selected_event["id"])
                st.success("Tədbir silindi.")
                st.rerun()
            except Exception:
                st.error("Tədbiri silmək mümkün olmadı.")


def main():
    if not initialize_app():
        st.stop()

    user = st.session_state.get("user")

    if not user:
        login_page()
        return

    st.title("🎓 Universitet Tədbirləri")
    st.sidebar.write(f"İstifadəçi: **{user['full_name']}**")
    st.sidebar.caption(f"Rol: {user['role']}")

    pages = ["Tədbirlər", "Mənim qeydiyyatlarım"]
    if user["role"] == "admin":
        pages.extend(["Statistika", "İdarəetmə"])

    selected_page = st.sidebar.radio("Menyu", pages)

    if st.sidebar.button("Çıxış"):
        st.session_state.pop("user", None)
        st.rerun()

    try:
        if selected_page == "Tədbirlər":
            events_page(user)
        elif selected_page == "Mənim qeydiyyatlarım":
            my_registrations_page(user)
        elif selected_page == "Statistika":
            statistics_page()
        elif selected_page == "İdarəetmə":
            admin_page()
    except Exception:
        st.error("Gözlənilməz xəta baş verdi. Yenidən cəhd edin.")


if __name__ == "__main__":
    main()
