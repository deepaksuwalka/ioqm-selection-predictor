import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import re


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="IOQM Selection Predictor",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ============================================================
# SESSION STATE
# ============================================================

if "prediction_done" not in st.session_state:
    st.session_state.prediction_done = False

if "status" not in st.session_state:
    st.session_state.status = None

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "student_marks" not in st.session_state:
    st.session_state.student_marks = None

if "cutoff_marks" not in st.session_state:
    st.session_state.cutoff_marks = None


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    header {
        visibility: hidden;
    }

    .stApp {
        background: linear-gradient(
            135deg,
            #f3e8ff 0%,
            #f8f9ff 45%,
            #ffffff 100%
        );
    }

    .block-container {
        max-width: 850px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        color: #2d1b4e;
        margin-top: 0.5rem;
        margin-bottom: 0.3rem;
    }

    .subtitle {
        text-align: center;
        color: #666666;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #4b1f6f;
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #d8b4fe;
    }

    .stTextInput label,
    .stSelectbox label,
    .stDateInput label,
    .stNumberInput label {
        font-weight: 600 !important;
    }

    .stTextInput input,
    .stNumberInput input {
        border-radius: 8px !important;
    }

    .stFormSubmitButton button {
        width: 100%;
        height: 3.2rem;
        border-radius: 10px;
        font-size: 1.1rem;
        font-weight: 700;
    }

    .result-card-qualified {
        background: #ecfdf3;
        border: 2px solid #22c55e;
        padding: 30px;
        border-radius: 18px;
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .result-card-not-likely {
        background: #fff7ed;
        border: 2px solid #f59e0b;
        padding: 30px;
        border-radius: 18px;
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .result-icon {
        font-size: 3rem;
        margin-bottom: 10px;
    }

    .result-name {
        font-size: 1.7rem;
        font-weight: 700;
        color: #292929;
        margin-bottom: 10px;
    }

    .probably-qualified {
        color: #15803d;
        font-size: 2rem;
        font-weight: 800;
        margin: 10px 0;
    }

    .selection-not-likely {
        color: #c2410c;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 10px 0;
    }

    .result-description {
        color: #555555;
        font-size: 1rem;
        line-height: 1.6;
        margin-top: 10px;
    }

    .marks-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-top: 15px;
        margin-bottom: 20px;
    }

    .marks-label {
        color: #666666;
        font-size: 1rem;
        font-weight: 600;
    }

    .marks-value {
        color: #4b1f6f;
        font-size: 2.5rem;
        font-weight: 800;
        margin-top: 5px;
    }

    .disclaimer-box {
        background: #fffbea;
        border: 1px solid #facc15;
        border-radius: 12px;
        padding: 18px;
        margin-top: 20px;
        margin-bottom: 20px;
        color: #713f12;
        font-size: 0.92rem;
        line-height: 1.6;
    }

    .footer-text {
        text-align: center;
        color: #888888;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-bottom: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================

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


# ============================================================
# LOAD CUTOFF DATA
# ============================================================

@st.cache_data(ttl=300)
def load_cutoff_data():

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet("Cutoff_Data")

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    if df.empty:
        raise ValueError("Cutoff_Data sheet is empty.")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Required columns
    required_columns = [
        "Class",
        "State",
        "Cut Off Marks",
        "Gender"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns in Cutoff_Data: "
            + ", ".join(missing_columns)
        )

    # Clean State
    df["State"] = (
        df["State"]
        .astype(str)
        .str.strip()
    )

    # Clean Gender
    df["Gender"] = (
        df["Gender"]
        .astype(str)
        .str.strip()
    )

    # Convert Class
    df["Class"] = pd.to_numeric(
        df["Class"],
        errors="coerce"
    )

    # Convert Cut Off Marks
    df["Cut Off Marks"] = pd.to_numeric(
        df["Cut Off Marks"],
        errors="coerce"
    )

    # Remove invalid rows
    df = df.dropna(
        subset=[
            "Class",
            "State",
            "Gender",
            "Cut Off Marks"
        ]
    )

    return df


# ============================================================
# SAVE STUDENT RESPONSE
# ============================================================

def save_student_response(student_data):

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet(
        "Student_Responses"
    )

    worksheet.append_row(
        student_data,
        value_input_option="USER_ENTERED"
    )


# ============================================================
# CHECK DUPLICATE REGISTRATION
# ============================================================

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

    registration_values = (
        df["IOQM Registration No."]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return registration_values.eq(
        str(registration_number).strip().lower()
    ).any()


# ============================================================
# HEADER / LOGO
# ============================================================

logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])

with logo_col2:

    st.image(
        "logo.png",
        width="stretch"
    )


st.markdown(
    """
    <div class="main-title">
        🎯 IOQM Selection Predictor
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="subtitle">
        Enter your details and marks to get an
        estimated selection prediction based on
        the available cutoff data.
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# LOAD CUTOFF DATA
# ============================================================

try:

    cutoff_df = load_cutoff_data()

except Exception as e:

    st.error(
        "Unable to connect to the cutoff database."
    )

    st.exception(e)

    st.stop()


# ============================================================
# OPTIONS
# ============================================================

gender_options = sorted(
    cutoff_df["Gender"]
    .dropna()
    .unique()
    .tolist()
)

state_options = sorted(
    cutoff_df["State"]
    .dropna()
    .unique()
    .tolist()
)

class_options = sorted(
    cutoff_df["Class"]
    .dropna()
    .unique()
    .tolist()
)


# ============================================================
# STUDENT FORM
# ============================================================

with st.form("selection_form"):

    # --------------------------------------------------------
    # STUDENT DETAILS
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="section-title">
            👤 Student Details
        </div>
        """,
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


    # --------------------------------------------------------
    # SELECTION DETAILS
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="section-title">
            📊 Selection Details
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        state = st.selectbox(
            "State *",
            state_options
        )

    with col2:

        selected_class = st.selectbox(
            "Class *",
            class_options
        )

    marks = st.number_input(
        "Marks Obtained *",
        min_value=0.0,
        step=1.0,
        format="%.0f"
    )


    # --------------------------------------------------------
    # DECLARATION & CONSENT
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="section-title">
            📋 Declaration & Consent
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        **1. I/We hereby solemnly declare that the information
        provided in this form are true to the best of my
        knowledge and belief.**
        """
    )

    st.markdown(
        """
        **2. I/We give our full consent to PhysicsWallah for
        using the above-mentioned assets for the above-said
        purposes.**
        """
    )

    st.markdown(
        """
        **3. Further, as the parent/guardian of the student,
        I undertake to monitor their studies and behaviour,
        particularly their emotional well-being, throughout
        their time at the institute. Should my child encounter
        any unavoidable circumstances, engage in self-destructive
        activities, or be found guilty of improper conduct/
        behaviour in class, Telegram groups, or any medium of
        exchange, I will not hold the institute or its management
        responsible. I understand and agree that any decision
        taken by PhysicsWallah will be final in all circumstances
        or situations.**
        """
    )

    st.markdown("---")

    consent_given = st.checkbox(
        "I have read and understood the above terms and "
        "voluntarily give my consent to PhysicsWallah Ltd. *"
    )


    # --------------------------------------------------------
    # PREDICTOR DISCLAIMER
    # --------------------------------------------------------

    st.warning(
        """
        **Important:** This tool provides an estimated/predicted
        selection status based on the cutoff data available in
        the system. It is **not an official IOQM result or
        confirmation of selection**. Final selection is subject
        to the official result and selection criteria announced
        by the concerned authority.
        """
    )

    st.write("")

    submitted = st.form_submit_button(
        "🔍 CHECK MY SELECTION",
        width="stretch"
    )


# ============================================================
# FORM SUBMISSION
# ============================================================

if submitted:

    # --------------------------------------------------------
    # VALIDATE NAME
    # --------------------------------------------------------

    if not name.strip():

        st.error(
            "Please enter your full name."
        )

        st.stop()


    # --------------------------------------------------------
    # VALIDATE EMAIL
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # VALIDATE PHONE
    # --------------------------------------------------------

    if not phone.strip():

        st.error(
            "Please enter your phone number."
        )

        st.stop()

    clean_phone = re.sub(
        r"\D",
        "",
        phone
    )

    if len(clean_phone) < 10:

        st.error(
            "Please enter a valid phone number."
        )

        st.stop()


    # --------------------------------------------------------
    # VALIDATE ROLL NUMBER
    # --------------------------------------------------------

    if not roll_no.strip():

        st.error(
            "Please enter your roll number."
        )

        st.stop()


    # --------------------------------------------------------
    # VALIDATE IOQM REGISTRATION NUMBER
    # --------------------------------------------------------

    if not ioqm_registration_no.strip():

        st.error(
            "Please enter your IOQM Registration Number."
        )

        st.stop()


    # --------------------------------------------------------
    # VALIDATE CONSENT
    # --------------------------------------------------------

    if not consent_given:

        st.error(
            "Please read and accept the Declaration & Consent "
            "before checking your selection prediction."
        )

        st.stop()


    # ========================================================
    # CHECK DUPLICATE REGISTRATION
    # ========================================================

    with st.spinner(
        "Checking your registration..."
    ):

        if registration_exists(
            ioqm_registration_no
        ):

            st.warning(
                "⚠️ A prediction has already been generated "
                "for this IOQM Registration Number."
            )

            st.info(
                "Each IOQM Registration Number can be used "
                "only once."
            )

            st.stop()


    # ========================================================
    # FIND MATCHING CUTOFF
    # ========================================================

    matching_rows = cutoff_df[
        (
            cutoff_df["Class"]
            == selected_class
        )
        &
        (
            cutoff_df["State"]
            .str.lower()
            .str.strip()
            ==
            state.lower().strip()
        )
        &
        (
            cutoff_df["Gender"]
            .str.lower()
            .str.strip()
            ==
            gender.lower().strip()
        )
    ]


    # ========================================================
    # CHECK CUTOFF
    # ========================================================

    if matching_rows.empty:

        st.warning(
            "No cutoff data was found for the selected "
            "Class, State and Gender."
        )

        st.stop()


    # ========================================================
    # GET CUTOFF
    # ========================================================

    cutoff_marks = matching_rows.iloc[0][
        "Cut Off Marks"
    ]


    # ========================================================
    # DETERMINE PREDICTION
    # ========================================================

    if marks >= cutoff_marks:

        status = "PROBABLY QUALIFIED"

    else:

        status = "SELECTION MAY NOT BE LIKELY"


    # ========================================================
    # TIMESTAMP
    # ========================================================

    submission_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    consent_timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    # ========================================================
    # SAVE DATA
    # ========================================================

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

        submission_time,

        "Yes",

        consent_timestamp

    ]


    # ========================================================
    # SAVE TO GOOGLE SHEETS
    # ========================================================

    try:

        save_student_response(
            student_data
        )

    except Exception as e:

        st.error(
            "Your prediction was calculated, but there was "
            "an error saving your response."
        )

        st.exception(e)

        st.stop()


    # ========================================================
    # SAVE RESULT TO SESSION STATE
    # ========================================================

    st.session_state.prediction_done = True

    st.session_state.status = status

    st.session_state.student_name = name.strip()

    st.session_state.student_marks = marks

    st.session_state.cutoff_marks = cutoff_marks


# ============================================================
# DISPLAY RESULT
# ============================================================

if st.session_state.prediction_done:

    st.divider()


    # --------------------------------------------------------
    # PROBABLY QUALIFIED
    # --------------------------------------------------------

    if st.session_state.status == "PROBABLY QUALIFIED":

        st.success(
            f"🎉 Congratulations, {st.session_state.student_name}!"
        )

        st.markdown(
            "## 🎉 YOU ARE PROBABLY QUALIFIED"
        )

        st.write(
            "Based on the cutoff data currently available "
            "in our system, your marks indicate that you "
            "may be eligible for selection."
        )


    # --------------------------------------------------------
    # SELECTION MAY NOT BE LIKELY
    # --------------------------------------------------------

    else:

        st.warning(
            f"Thank you, {st.session_state.student_name}."
        )

        st.markdown(
            "## 📊 SELECTION MAY NOT BE LIKELY"
        )

        st.write(
            "Based on the cutoff data currently available "
            "in our system, your marks are below the "
            "indicative cutoff used for this prediction."
        )

        st.write(
            "This does not constitute an official result."
        )


    # ========================================================
    # SHOW MARKS
    # ========================================================

    st.subheader("Your Marks")

    st.metric(
        label="Marks Obtained",
        value=f"{st.session_state.student_marks:.0f}"
    )


    # ========================================================
    # SHOW CUTOFF
    # ========================================================

    st.metric(
        label="Indicative Cutoff",
        value=f"{st.session_state.cutoff_marks:.0f}"
    )


    # ========================================================
    # IMPORTANT DISCLAIMER
    # ========================================================

    st.warning(
        """
        **Disclaimer**

        This is a selection predictor based on the cutoff data
        available at the time of prediction.

        The result shown here is only an estimate and should not
        be considered an official confirmation of IOQM selection.

        Final selection will be based solely on the official result
        and criteria announced by the concerned authority.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer-text">
        © 2026 PhysicsWallah | IOQM Selection Predictor
    </div>
    """,
    unsafe_allow_html=True
)