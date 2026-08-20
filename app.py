import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import re


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="IOQM Selection Predictor",
    page_icon="🎯",
    layout="centered"
)


# --------------------------------------------------
# GOOGLE SHEETS CONNECTION
# --------------------------------------------------

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


# --------------------------------------------------
# LOAD CUTOFF DATA
# --------------------------------------------------

@st.cache_data(ttl=300)
def load_cutoff_data():

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet("Cutoff_Data")

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Clean text columns
    df["State"] = df["State"].astype(str).str.strip()
    df["Gender"] = df["Gender"].astype(str).str.strip()

    # Convert numerical columns
    df["Class"] = pd.to_numeric(
        df["Class"],
        errors="coerce"
    )

    df["Cut Off Marks"] = pd.to_numeric(
        df["Cut Off Marks"],
        errors="coerce"
    )

    return df


# --------------------------------------------------
# SAVE STUDENT RESPONSE
# --------------------------------------------------

def save_student_response(student_data):

    spreadsheet = get_google_sheet()

    worksheet = spreadsheet.worksheet(
        "Student_Responses"
    )

    worksheet.append_row(student_data)


# --------------------------------------------------
# CHECK DUPLICATE REGISTRATION
# --------------------------------------------------

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


# --------------------------------------------------
# APP TITLE
# --------------------------------------------------

st.title("🎯 IOQM Selection Predictor")

st.write(
    "Enter your details and marks to check your "
    "qualification status based on the available cutoff data."
)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

try:

    cutoff_df = load_cutoff_data()

except Exception as e:

    st.error(
        "Unable to connect to the cutoff database."
    )

    st.exception(e)

    st.stop()


# --------------------------------------------------
# FORM
# --------------------------------------------------

with st.form("selection_form"):

    st.subheader("Student Details")

    name = st.text_input(
        "Full Name *"
    )

    email = st.text_input(
        "Email ID *"
    )

    phone = st.text_input(
        "Phone Number *",
        max_chars=15
    )

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

    dob = st.date_input(
        "Date of Birth *",
        min_value=date(1990, 1, 1),
        max_value=date.today()
    )

    roll_no = st.text_input(
        "Roll Number *"
    )

    ioqm_registration_no = st.text_input(
        "IOQM Registration Number *"
    )

    st.subheader("Selection Details")

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

    submitted = st.form_submit_button(
        "Check My Selection",
        use_container_width=True
    )


# --------------------------------------------------
# FORM SUBMISSION
# --------------------------------------------------

if submitted:

    # -------------------------
    # VALIDATION
    # -------------------------

    if not name.strip():
        st.error("Please enter your name.")
        st.stop()

    if not email.strip():
        st.error("Please enter your email address.")
        st.stop()

    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.match(
        email_pattern,
        email.strip()
    ):
        st.error("Please enter a valid email address.")
        st.stop()

    if not phone.strip():
        st.error("Please enter your phone number.")
        st.stop()

    if not roll_no.strip():
        st.error("Please enter your roll number.")
        st.stop()

    if not ioqm_registration_no.strip():
        st.error(
            "Please enter your IOQM Registration Number."
        )
        st.stop()


    # -------------------------
    # DUPLICATE CHECK
    # -------------------------

    with st.spinner("Checking registration..."):

        if registration_exists(
            ioqm_registration_no
        ):

            st.warning(
                "A result has already been generated "
                "for this IOQM Registration Number."
            )

            st.stop()


    # -------------------------
    # FIND MATCHING CUTOFF
    # -------------------------

    matching_rows = cutoff_df[
        (
            cutoff_df["Class"] == selected_class
        )
        &
        (
            cutoff_df["State"].str.lower()
            == state.lower()
        )
        &
        (
            cutoff_df["Gender"].str.lower()
            == gender.lower()
        )
    ]


    # -------------------------
    # CHECK IF CUTOFF EXISTS
    # -------------------------

    if matching_rows.empty:

        st.warning(
            "No cutoff data was found for the selected "
            "Class, State and Gender."
        )

        st.stop()


    # -------------------------
    # GET CUTOFF
    # -------------------------

    cutoff_marks = matching_rows.iloc[0][
        "Cut Off Marks"
    ]


    # -------------------------
    # DETERMINE STATUS
    # -------------------------

    if marks >= cutoff_marks:

        status = "QUALIFIED"

    else:

        status = "NOT QUALIFIED"


    # -------------------------
    # SAVE RESPONSE
    # -------------------------

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


    # -------------------------
    # DISPLAY RESULT
    # -------------------------

    st.divider()

    if status == "QUALIFIED":

        st.success(
            f"🎉 Congratulations, {name}!"
        )

        st.header(
            "You are QUALIFIED!"
        )

    else:

        st.error(
            f"Thank you, {name}."
        )

        st.header(
            "You are NOT QUALIFIED."
        )


    # -------------------------
    # RESULT DETAILS
    # -------------------------

    col1, col2 = st.columns(2)

    col1.metric(
        "Your Marks",
        marks
    )

    col2.metric(
        "Cutoff Marks",
        cutoff_marks
    )

    st.info(
        f"Status: {status}"
    )