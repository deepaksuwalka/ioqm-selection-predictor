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
        line-height: 1.6;
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
    .stNumberInput label,
    .stCheckbox label {
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

    .footer-text {
        text-align: center;
        color: #888888;
        font-size: 0.85rem;
        margin-top: 3rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


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

    worksheet = spreadsheet.worksheet(
        "Cutoff_Data"
    )

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    if df.empty:
        raise ValueError(
            "Cutoff_Data sheet is empty."
        )

    # Clean column names
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # Required columns
    required_columns = [
        "Class",
        "State",
        "Gender",
        "Cut Off Marks"
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


# ==================================================
# SAVE STUDENT RESPONSE
# ==================================================

def save_student_response(student_data):

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet(
        "Student_Responses"
    )

    cleaned_data = []

    for value in student_data:

        if value is None:

            cleaned_data.append("")
            continue

        try:

            if hasattr(value, "item"):

                value = value.item()

        except Exception:

            pass

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool
            )
        ):

            cleaned_data.append(value)

        else:

            cleaned_data.append(
                str(value)
            )

    worksheet.append_row(
        cleaned_data,
        value_input_option="USER_ENTERED"
    )


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
        .str.lower()
        .eq(
            str(
                registration_number
            )
            .strip()
            .lower()
        )
        .any()
    )


# ==================================================
# HEADER / LOGO
# ==================================================

try:

    logo_col1, logo_col2, logo_col3 = st.columns(
        [1, 2, 1]
    )

    with logo_col2:

        st.image(
            "logo.png",
            width="stretch"
        )

except Exception:

    pass


# ==================================================
# PAGE TITLE
# ==================================================

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
        Enter your details and marks to get an estimated
        selection prediction based on the cutoff data
        currently available in the system.
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# LOAD CUTOFF DATA
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
# FORM OPTIONS
# ==================================================

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

class_options = [
    int(x)
    if float(x).is_integer()
    else float(x)
    for x in class_options
]


# ==================================================
# DOB SETTINGS
# ==================================================

MIN_DOB = date(2007, 1, 1)
MAX_DOB = date(2014, 12, 12)

dob_years = list(
    range(
        MIN_DOB.year,
        MAX_DOB.year + 1
    )
)

months = [
    (1, "January"),
    (2, "February"),
    (3, "March"),
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
    (12, "December")
]


# ==================================================
# STUDENT FORM
# ==================================================

with st.form("selection_form"):

    # ==============================================
    # STUDENT DETAILS
    # ==============================================

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

        st.empty()


    # ==============================================
    # DATE OF BIRTH
    # ==============================================

    st.markdown(
        "**Date of Birth * **"
    )

    dob_col1, dob_col2, dob_col3 = st.columns(
        [1, 1.5, 1]
    )

    with dob_col1:

        dob_day = st.selectbox(
            "Day",
            list(range(1, 32)),
            index=0
        )

    with dob_col2:

        dob_month = st.selectbox(
            "Month",
            months,
            format_func=lambda x: x[1],
            index=0
        )

    with dob_col3:

        dob_year = st.selectbox(
            "Year",
            dob_years,
            index=len(dob_years) - 1
        )


    # ==============================================
    # CREATE DOB
    # ==============================================

    try:

        selected_dob = date(
            dob_year,
            dob_month[0],
            dob_day
        )

    except ValueError:

        selected_dob = None


    # ==============================================
    # ROLL & REGISTRATION
    # ==============================================

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


    # ==============================================
    # SELECTION DETAILS
    # ==============================================

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
        step=1.0
    )


    # ==============================================
    # TERMS & CONDITIONS
    # ==============================================

    st.markdown(
        "<div style='height:10px'></div>",
        unsafe_allow_html=True
    )

    terms_col1, terms_col2 = st.columns(
        [0.72, 0.28]
    )

    with terms_col1:

        consent = st.checkbox(
            "I have read and agree to the Terms & Conditions"
        )

    with terms_col2:

        with st.popover(
            "Terms & Conditions"
        ):

            st.markdown(
                """
## Terms & Conditions

**Greetings from PhysicsWallah Limited!**

At PhysicsWallah Ltd. (PW), we provide personalized academic and Olympiad training programs.

By submitting this form, I give PW permission to use my/my child's name, scores, photographs, videos, and testimonials for promotional and educational purposes on platforms such as social media, television, hoardings, interviews, websites, and the PW app.

PW may also share details of future exam participation for publicity or academic updates, while ensuring full compliance with Indian laws, PW's User and Privacy Policies, and GDPR standards. PW guarantees that no data will be misused.

### Purpose of Consent

To allow PW to feature the student's achievements, learning journey, and experiences in campaigns that motivate other aspirants.

### Conditions of Usage

**Preliminary Consent:** This is initial consent for use of personal and media details.

**Final Consent:** PW may contact again for written approval before publishing.

**Opt-Out Option:** Consent can be withdrawn anytime by notifying PW in writing.

**No Misuse:** PW will use all data responsibly.

**No Monetary Benefit:** No financial or other compensation is applicable.

**Duration:** Consent remains valid until withdrawn in writing.

### Final Consent for Promotional Use

As discussed earlier, we seek your final consent to feature your success story, including your name, photographs, videos, and testimonials, in the following media:

- Print publications (brochures, magazines, posters)

- Digital platforms (official websites, online blogs, e-magazines)

- Social media platforms (YouTube, Instagram, Facebook, LinkedIn, etc.)

- Video campaigns, advertisements, and other publicity materials

**1. I/We hereby solemnly declare that the information provided in this form are true to the best of my knowledge and belief.**

**2. I/We give our full consent to PhysicsWallah for using the above-mentioned assets for the above-said purposes.**

**3. Further, as the parent/guardian of the student, I undertake to monitor their studies and behaviour, particularly their emotional well-being, throughout their time at the institute. Should my child encounter any unavoidable circumstances, engage in self-destructive activities, or be found guilty of improper conduct/behaviour in class, Telegram groups, or any medium of exchange, I will not hold the institute or its management responsible. I understand and agree that any decision taken by PhysicsWallah will be final in all circumstances or situations.**
                """
            )


    st.write("")


    # ==============================================
    # SUBMIT BUTTON
    # ==============================================

    submitted = st.form_submit_button(
        "🔍 CHECK MY SELECTION PREDICTION",
        width="stretch"
    )


# ==================================================
# FORM SUBMISSION
# ==================================================

if submitted:


    # ==============================================
    # VALIDATE NAME
    # ==============================================

    if not name.strip():

        st.error(
            "Please enter your full name."
        )

        st.stop()


    # ==============================================
    # VALIDATE EMAIL
    # ==============================================

    if not email.strip():

        st.error(
            "Please enter your email address."
        )

        st.stop()


    email_pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    if not re.match(
        email_pattern,
        email.strip()
    ):

        st.error(
            "Please enter a valid email address."
        )

        st.stop()


    # ==============================================
    # VALIDATE PHONE
    # ==============================================

    if not phone.strip():

        st.error(
            "Please enter your phone number."
        )

        st.stop()


    cleaned_phone = re.sub(
        r"[\s\-\(\)]",
        "",
        phone
    )


    if not re.match(
        r"^\+?\d{10,15}$",
        cleaned_phone
    ):

        st.error(
            "Please enter a valid phone number."
        )

        st.stop()


    # ==============================================
    # VALIDATE DOB
    # ==============================================

    if selected_dob is None:

        st.error(
            "Please select a valid Date of Birth."
        )

        st.stop()


    if (
        selected_dob < MIN_DOB
        or selected_dob > MAX_DOB
    ):

        st.error(
            "Date of Birth must be between "
            "01 January 2007 and 12 December 2014."
        )

        st.stop()


    # ==============================================
    # VALIDATE ROLL NUMBER
    # ==============================================

    if not roll_no.strip():

        st.error(
            "Please enter your roll number."
        )

        st.stop()


    # ==============================================
    # VALIDATE REGISTRATION NUMBER
    # ==============================================

    if not ioqm_registration_no.strip():

        st.error(
            "Please enter your IOQM Registration Number."
        )

        st.stop()


    # ==============================================
    # VALIDATE MARKS
    # ==============================================

    if marks < 0:

        st.error(
            "Please enter valid marks."
        )

        st.stop()


    # ==============================================
    # CHECK DUPLICATE REGISTRATION
    # ==============================================

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


    # ==============================================
    # FIND MATCHING CUTOFF
    # ==============================================

    selected_class_numeric = float(
        selected_class
    )


    matching_rows = cutoff_df[
        (
            cutoff_df["Class"]
            == selected_class_numeric
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


    # ==============================================
    # CHECK IF CUTOFF EXISTS
    # ==============================================

    if matching_rows.empty:

        st.warning(
            "No prediction data was found for the selected "
            "Class, State and Gender."
        )

        st.stop()


    # ==============================================
    # GET CUTOFF
    # ==============================================

    cutoff_marks = float(
        matching_rows.iloc[0][
            "Cut Off Marks"
        ]
    )


    # ==============================================
    # CALCULATE SELECTION CHANCE
    # ==============================================

    marks_difference = (
        float(marks)
        -
        float(cutoff_marks)
    )


    if marks_difference >= 0:

        selection_chance = 100

        prediction_status = (
            "PROBABLY QUALIFIED"
        )

        result_type = (
            "positive"
        )

        result_icon = "🎉"

        result_message = (
            "Based on the cutoff data currently available "
            "in our system, your marks indicate a strong "
            "possibility of selection."
        )


    elif marks_difference >= -1:

        selection_chance = 90

        prediction_status = (
            "HIGH POSSIBILITY OF SELECTION"
        )

        result_type = (
            "warning"
        )

        result_icon = "✨"

        result_message = (
            "Your marks are very close to the predicted "
            "selection range. There is a high possibility "
            "of selection based on the available data."
        )


    elif marks_difference >= -2:

        selection_chance = 80

        prediction_status = (
            "GOOD POSSIBILITY OF SELECTION"
        )

        result_type = (
            "warning"
        )

        result_icon = "👍"

        result_message = (
            "Your marks indicate a good possibility of "
            "selection based on the cutoff data currently "
            "available."
        )


    elif marks_difference >= -3:

        selection_chance = 70

        prediction_status = (
            "POSSIBLE SELECTION"
        )

        result_type = (
            "warning"
        )

        result_icon = "📊"

        result_message = (
            "Your marks are within the predicted range where "
            "selection may still be possible."
        )


    elif marks_difference >= -4:

        selection_chance = 60

        prediction_status = (
            "MODERATE POSSIBILITY OF SELECTION"
        )

        result_type = (
            "warning"
        )

        result_icon = "📈"

        result_message = (
            "Your marks indicate a moderate possibility of "
            "selection based on the available prediction data."
        )


    elif marks_difference >= -5:

        selection_chance = 50

        prediction_status = (
            "SELECTION POSSIBILITY EXISTS"
        )

        result_type = (
            "warning"
        )

        result_icon = "🔎"

        result_message = (
            "Your marks are close to the predicted range. "
            "Selection may be possible depending on the "
            "final official criteria."
        )


    else:

        selection_chance = 0

        prediction_status = (
            "SELECTION NOT LIKELY"
        )

        result_type = (
            "negative"
        )

        result_icon = "📋"

        result_message = (
            "Based on the cutoff data currently available "
            "in our system, selection does not appear likely. "
            "However, the final outcome depends on the official "
            "selection criteria."
        )


    # ==============================================
    # PREPARE DATA FOR GOOGLE SHEETS
    # ==============================================

    submission_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    student_data = [

        # Student Details
        str(name.strip()),
        str(email.strip()),
        str(cleaned_phone),
        str(gender),

        # DOB
        selected_dob.strftime(
            "%d/%m/%Y"
        ),

        # Roll Number
        str(roll_no.strip()),

        # IOQM Registration Number
        str(ioqm_registration_no.strip()),

        # State
        str(state),

        # Class
        int(float(selected_class)),

        # Marks
        float(marks),

        # Internal Cutoff
        float(cutoff_marks),

        # Prediction Status
        str(prediction_status),

        # Selection Chance
        int(selection_chance),

        # Terms & Conditions Consent
        "Yes" if consent else "No",

        # Submission Time
        str(submission_time)
    ]


    # ==============================================
    # SAVE RESPONSE
    # ==============================================

    try:

        save_student_response(
            student_data
        )

    except Exception as e:

        st.error(
            "Your prediction was calculated, but there "
            "was an error saving your response."
        )

        st.exception(e)

        st.stop()


    # ==============================================
    # DISPLAY RESULT
    # ==============================================

    st.divider()


    # ==============================================
    # POSITIVE RESULT
    # ==============================================

    if result_type == "positive":

        st.success(
            f"🎉 Congratulations, {name.strip()}!"
        )

        st.subheader(
            "You Are Probably Qualified"
        )


    # ==============================================
    # WARNING RESULT
    # ==============================================

    elif result_type == "warning":

        st.warning(
            f"{result_icon} Thank you, {name.strip()}!"
        )

        st.subheader(
            prediction_status
        )


    # ==============================================
    # NEGATIVE RESULT
    # ==============================================

    else:

        st.error(
            f"Thank you, {name.strip()}"
        )

        st.subheader(
            "Selection Does Not Appear Likely"
        )


    # ==============================================
    # RESULT SUMMARY
    # ==============================================

    if result_type == "negative":

        st.metric(
            "Your Marks",
            f"{float(marks):g}"
        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Your Marks",
                f"{float(marks):g}"
            )

        with col2:

            st.metric(
                "Estimated Selection Chance",
                f"{selection_chance}%"
            )


    # ==============================================
    # PREDICTION MESSAGE
    # ==============================================

    st.info(
        result_message
    )


    # ==============================================
    # DISCLAIMER
    # ==============================================

    st.warning(
        """
**Disclaimer**

This is a selection predictor based on the cutoff data
available at the time of prediction. The result shown here
is only an estimate and should not be considered an official
confirmation of IOQM selection.

Final selection will be based solely on the official result
and criteria announced by the concerned authority.
        """
    )


# ==================================================
# FOOTER
# ==================================================

st.markdown(
    """
    <div class="footer-text">
        © 2026 IOQM Selection Predictor
    </div>
    """,
    unsafe_allow_html=True
)