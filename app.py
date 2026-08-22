import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import re


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="IOQM Selection Predictor",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>

/* Hide Streamlit elements */
#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}


/* PAGE BACKGROUND */

.stApp {
    background: linear-gradient(
        135deg,
        #f3e8ff 0%,
        #f8f9ff 45%,
        #ffffff 100%
    );
}


/* MAIN CONTENT */

.block-container {
    max-width: 850px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}


/* TITLE */

.main-title {
    text-align: center;
    font-size: 2.5rem;
    font-weight: 800;
    color: #2d1b4e;
    margin-top: 0.5rem;
    margin-bottom: 0.3rem;
}


/* SUBTITLE */

.subtitle {
    text-align: center;
    color: #666666;
    font-size: 1.05rem;
    margin-bottom: 2rem;
}


/* SECTION TITLE */

.section-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #4b1f6f;
    margin-top: 1rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #d8b4fe;
}


/* FORM LABELS */

.stTextInput label,
.stSelectbox label,
.stDateInput label,
.stNumberInput label {
    font-weight: 600 !important;
}


/* INPUT FIELDS */

.stTextInput input,
.stNumberInput input {
    border-radius: 8px !important;
}


/* BUTTON */

.stFormSubmitButton button {
    width: 100%;
    height: 3.2rem;
    border-radius: 10px;
    font-size: 1.1rem;
    font-weight: 700;
}


/* QUALIFIED RESULT CARD */

.qualified-card {
    background: #eaf8ef;
    border: 2px solid #22c55e;
    padding: 30px;
    border-radius: 18px;
    text-align: center;
    margin-top: 20px;
}


/* NOT QUALIFIED RESULT CARD */

.not-qualified-card {
    background: #fff0f0;
    border: 2px solid #ef4444;
    padding: 30px;
    border-radius: 18px;
    text-align: center;
    margin-top: 20px;
}


/* RESULT HEADINGS */

.result-name {
    font-size: 1.7rem;
    font-weight: 700;
    margin-bottom: 10px;
}


.qualified-text {
    color: #15803d;
    font-size: 2rem;
    font-weight: 800;
}


.not-qualified-text {
    color: #dc2626;
    font-size: 2rem;
    font-weight: 800;
}


.result-description {
    color: #555555;
    font-size: 1rem;
    margin-top: 10px;
}


/* FOOTER */

.footer-text {
    text-align: center;
    color: #888888;
    font-size: 0.85rem;
    margin-top: 3rem;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# GOOGLE SHEETS CONNECTION
# ==================================================

@st.cache_resource
def get_google_sheet():

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(
        st.secrets["SPREADSHEET_ID"]
    )

    return spreadsheet


# ==================================================
# LOAD CUTOFF DATA
# ==================================================

@st.cache_data(ttl=300)
def load_cutoff_data():

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet("Cutoff_Data")

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    df.columns = df.columns.str.strip()

    df["State"] = (
        df["State"]
        .astype(str)
        .str.strip()
    )

    df["Gender"] = (
        df["Gender"]
        .astype(str)
        .str.strip()
    )

    df["Class"] = pd.to_numeric(
        df["Class"],
        errors="coerce"
    )

    df["Cut Off Marks"] = pd.to_numeric(
        df["Cut Off Marks"],
        errors="coerce"
    )

    return df


# ==================================================
# SAVE STUDENT RESPONSE
# ==================================================

def save_student_response(student_data):

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet(
        "Student_Responses"
    )

    worksheet.append_row(student_data)


# ==================================================
# CHECK DUPLICATE REGISTRATION
# ==================================================

def registration_exists(registration_number):

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet(
        "Student_Responses"
    )

    records = worksheet.get_all_records()

    if not records:
        return False

    df = pd.DataFrame(records)

    if "IOQM Registration No." not in df.columns:
        return False

    return (
        df["IOQM Registration No."]
        .astype(str)
        .str.strip()
        .eq(str(registration_number).strip())
        .any()
    )


# ==================================================
# HEADER / LOGO
# ==================================================

logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])

with logo_col2:
    st.image(
        "logo.png",
        width="stretch"
    )


st.markdown(
    '<div class="main-title">🎯 IOQM Selection Predictor</div>',
    unsafe_allow_html=True
)


st.markdown(
    '<div class="subtitle">Enter your details and marks to check your qualification status based on the available cutoff data.</div>',
    unsafe_allow_html=True
)


# ==================================================
# LOAD DATA
# ==================================================

try:

    cutoff_df = load_cutoff_data()

except Exception as e:

    st.error(
        "Unable to connect to the cutoff database."
    )

    st.exception(e)

    st.stop()


# ==================================================
# FORM
# ==================================================

with st.form("selection_form"):

    st.markdown(
        '<div class="section-title">👤 Student Details</div>',
        unsafe_allow_html=True
    )


    name = st.text_input(
        "Full Name *",
        placeholder="Enter your full name"
    )


    col1, col2 = st.columns(2)

    with col1:

        email = st.text_input(
            "Email ID *",
            placeholder="example@email.com"
        )

    with col2:

        phone = st.text_input(
            "Phone Number *",
            placeholder="Enter phone number",
            max_chars=15
        )


    col1, col2 = st.columns(2)

    with col1:

        gender_options = sorted(
            cutoff_df["Gender"]
            .dropna()
            .unique()
            .tolist()
        )

        gender = st.selectbox(
            "Gender *",
            gender_options
        )

    with col2:

        dob = st.date_input(
            "Date of Birth *",
            min_value=date(1990, 1, 1),
            max_value=date.today()
        )


    col1, col2 = st.columns(2)

    with col1:

        roll_no = st.text_input(
            "Roll Number *",
            placeholder="Enter roll number"
        )

    with col2:

        ioqm_registration_no = st.text_input(
            "IOQM Registration No. *",
            placeholder="Enter registration number"
        )


    st.markdown(
        '<div class="section-title">📊 Selection Details</div>',
        unsafe_allow_html=True
    )


    col1, col2 = st.columns(2)

    with col1:

        state_options = sorted(
            cutoff_df["State"]
            .dropna()
            .unique()
            .tolist()
        )

        state = st.selectbox(
            "State *",
            state_options
        )

    with col2:

        class_options = sorted(
            cutoff_df["Class"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_class = st.selectbox(
            "Class *",
            class_options
        )


    marks = st.number_input(
        "Marks Obtained *",
        min_value=0.0,
        step=1.0
    )


    st.write("")


    submitted = st.form_submit_button(
        "🔍 CHECK MY RESULT",
        width="stretch"
    )


# ==================================================
# FORM SUBMISSION
# ==================================================

if submitted:

    # VALIDATE NAME

    if not name.strip():

        st.error(
            "Please enter your full name."
        )

        st.stop()


    # VALIDATE EMAIL

    if not email.strip():

        st.error(
            "Please enter your email address."
        )

        st.stop()


    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


    if not re.match(
        email_pattern,
        email.strip()
    ):

        st.error(
            "Please enter a valid email address."
        )

        st.stop()


    # VALIDATE PHONE

    if not phone.strip():

        st.error(
            "Please enter your phone number."
        )

        st.stop()


    # VALIDATE ROLL NUMBER

    if not roll_no.strip():

        st.error(
            "Please enter your roll number."
        )

        st.stop()


    # VALIDATE REGISTRATION NUMBER

    if not ioqm_registration_no.strip():

        st.error(
            "Please enter your IOQM Registration Number."
        )

        st.stop()


    # ==================================================
    # CHECK DUPLICATE
    # ==================================================

    with st.spinner(
        "Checking your registration..."
    ):

        if registration_exists(
            ioqm_registration_no
        ):

            st.warning(
                "⚠️ A result has already been generated for "
                "this IOQM Registration Number."
            )

            st.stop()


    # ==================================================
    # FIND CUTOFF
    # ==================================================

    matching_rows = cutoff_df[
        (
            cutoff_df["Class"] == selected_class
        )
        &
        (
            cutoff_df["State"]
            .str.lower()
            .str.strip()
            == state.lower().strip()
        )
        &
        (
            cutoff_df["Gender"]
            .str.lower()
            .str.strip()
            == gender.lower().strip()
        )
    ]


    if matching_rows.empty:

        st.warning(
            "No cutoff data was found for the selected "
            "Class, State and Gender."
        )

        st.stop()


    cutoff_marks = matching_rows.iloc[0][
        "Cut Off Marks"
    ]


    # ==================================================
    # DETERMINE RESULT
    # ==================================================

    if marks >= cutoff_marks:

        status = "QUALIFIED"

    else:

        status = "NOT QUALIFIED"


    # ==================================================
    # PREPARE DATA
    # ==================================================

    submission_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    student_data = [
        name.strip(),
        email.strip(),
        phone.strip(),
        gender,
        str(dob),
        roll_no.strip(),
        ioqm_registration_no.strip(),
        state,
        selected_class,
        marks,
        cutoff_marks,
        status,
        submission_time
    ]


    # ==================================================
    # SAVE RESPONSE
    # ==================================================

    try:

        save_student_response(
            student_data
        )

    except Exception as e:

        st.error(
            "Your result was calculated, but there was "
            "an error saving your response."
        )

        st.exception(e)

        st.stop()


    # ==================================================
    # DISPLAY RESULT
    # IMPORTANT: SINGLE-LINE HTML STRINGS
    # This prevents Streamlit from showing HTML as code.
    # ==================================================

    st.divider()


    if status == "QUALIFIED":

        st.markdown(
            f'<div class="qualified-card"><div style="font-size:3rem;">🎉</div><div class="result-name">Congratulations, {name}!</div><div class="qualified-text">YOU ARE QUALIFIED</div><div class="result-description">Based on the available cutoff data, you have qualified.</div></div>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f'<div class="not-qualified-card"><div style="font-size:3rem;">📋</div><div class="result-name">Thank you, {name}</div><div class="not-qualified-text">NOT QUALIFIED</div><div class="result-description">Based on the available cutoff data, your marks are below the required cutoff.</div></div>',
            unsafe_allow_html=True
        )


    # ==================================================
    # RESULT METRICS
    # ==================================================

    st.write("")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Your Marks",
            marks
        )

    with col2:

        st.metric(
            "Required Cutoff",
            cutoff_marks
        )


    # ==================================================
    # FINAL STATUS
    # ==================================================

    if status == "QUALIFIED":

        st.success(
            "Final Status: QUALIFIED"
        )

    else:

        st.error(
            "Final Status: NOT QUALIFIED"
        )


# ==================================================
# FOOTER
# ==================================================

st.markdown(
    '<div class="footer-text">© 2026 IOQM Selection Predictor</div>',
    unsafe_allow_html=True
)