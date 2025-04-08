import streamlit as st
import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from streamlit_tags import st_tags
from fpdf import FPDF

# Load .env
load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")

st.set_page_config(page_title="TalentScout_Hiring_Assistant", layout="centered")

st.markdown("""
    <style>
        textarea, input[type="text"] {
            border: 2px solid #4CAF50 !important;
            border-radius: 5px !important;
        }
        .stTextInput > div > div > input {
            border: 2px solid #4CAF50 !important;
            border-radius: 5px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 TalentScout Hiring Assistant")
st.markdown("Welcome! I'm your assistant for the initial screening process. Let's get started!")

# Session state init
def init_state():
    defaults = {
        'step': 0,
        'user_data': {},
        'questions_generated': False,
        'generated_questions': [],
        'data_saved': False,
        'tech_stack_temp': [],
        'answers': {},
        'submit_clicked': False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

questions = [
    "May I know your full name?",
    "Great! Can I get your email address?",
    "And your phone number?",
    "How many years of experience do you have?",
    "Which position are you applying for?",
    "What's your current location?",
    "Lastly, can you list your tech stack (languages, frameworks, tools)?"
]

keys = ["name", "email", "phone", "experience", "position", "location", "tech_stack"]
tech_suggestions = [
    "Python", "Java", "C++", "JavaScript", "HTML", "CSS", "SQL",
    "Django", "Flask", "React", "Node.js", "MongoDB", "MySQL",
    "TensorFlow", "PyTorch", "Keras", "Pandas", "NumPy",
    "Git", "Docker", "Kubernetes", "FastAPI", "TypeScript"
]

if st.session_state.step < len(questions):
    st.progress((st.session_state.step + 1) / len(questions))
    st.markdown(f"**Bot:** {questions[st.session_state.step]}")

    with st.form(key="input_form"):
        if st.session_state.step == len(questions) - 1:
            selected_techs = st_tags(
                label="💡 Type and press Enter to select tech skills:",
                text="Press enter to add",
                value=st.session_state.tech_stack_temp,
                suggestions=tech_suggestions,
                maxtags=10,
                key="tech_input"
            )
            submit = st.form_submit_button("➡️ Next")
            if submit and selected_techs:
                st.session_state.tech_stack_temp = selected_techs
                st.session_state.user_data[keys[st.session_state.step]] = ", ".join(selected_techs)
                st.session_state.step += 1
                st.rerun()
        else:
            default_val = st.session_state.user_data.get(keys[st.session_state.step], "")
            answer = st.text_input("You:", value=default_val, key=f"step_{st.session_state.step}")
            submit = st.form_submit_button("➡️ Next")
            if submit and answer:
                st.session_state.user_data[keys[st.session_state.step]] = answer
                st.session_state.step += 1
                st.rerun()

    col1, col2 = st.columns([1, 1])
    if col1.button("⬅️ Back", disabled=st.session_state.step == 0):
        st.session_state.step -= 1
        st.rerun()

elif st.session_state.user_data:
    def generate_questions(tech_stack):
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        prompt = f"Generate 5 short and relevant technical interview questions (1-2 lines only) for a candidate proficient in: {tech_stack}."
        payload = {"inputs": prompt}
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            result = response.json()
            if isinstance(result, list) and "generated_text" in result[0]:
                raw_text = result[0]["generated_text"]
                return [line.strip() for line in raw_text.split("\n") if line.strip() and line.strip()[0].isdigit()][:6]
            return ["❌ API error or bad response"]
        except Exception as e:
            return [f"❌ Error: {e}"]

    if not st.session_state.questions_generated:
        st.success("✅ Thank you! We've collected all your details.")
        if st.button("Answer These Questions"):
            output = generate_questions(st.session_state.user_data.get("tech_stack", ""))
            st.session_state.generated_questions = output
            st.session_state.questions_generated = True
            st.rerun()

    elif not st.session_state.submit_clicked:
        st.markdown("**🧠 Screening Questions: Please answer below**")
        for i, q in enumerate(st.session_state.generated_questions):
            st.markdown(f"**Q{i+1}.** {q}")
            st.session_state.answers[f"Q{i+1}"] = st.text_area(f"Your Answer {i+1}", value=st.session_state.answers.get(f"Q{i+1}", ""), key=f"answer_{i}")

        if st.button("📤 Submit Answers"):
            Path("data").mkdir(exist_ok=True)
            with open("data/candidates.json", "a") as f:
                json.dump({
                    "user": st.session_state.user_data,
                    "questions": st.session_state.generated_questions,
                    "answers": st.session_state.answers
                }, f, indent=2)
            st.session_state.submit_clicked = True
            st.rerun()

    else:
        def generate_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="TalentScout Hiring Report", ln=True, align="C")
            pdf.ln(5)
            pdf.set_font("Arial", 'B', size=12)
            pdf.cell(200, 10, txt="Candidate Details:", ln=True)
            pdf.set_font("Arial", size=11)
            for k, v in data['user'].items():
                pdf.cell(200, 8, txt=f"{k.capitalize()}: {v}", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", 'B', size=12)
            pdf.cell(200, 10, txt="Q&A:", ln=True)
            pdf.set_font("Arial", size=11)
            for i, q in enumerate(data['questions']):
                a = data['answers'].get(f"Q{i+1}", "")
                pdf.multi_cell(0, 8, txt=f"Q{i+1}: {q}\nA: {a}", align="L")
                pdf.ln(1)
            output_path = "data/report.pdf"
            pdf.output(output_path)
            return output_path

        st.markdown("### ✅ Your response is recorded. You may now leave or download your response.")
        pdf_path = generate_pdf({
            "user": st.session_state.user_data,
            "questions": st.session_state.generated_questions,
            "answers": st.session_state.answers
        })
        with open(pdf_path, "rb") as f:
            st.download_button(label="📄 Download Response as PDF", data=f, file_name="TalentScout_Report.pdf")

st.markdown("---")