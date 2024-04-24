import streamlit as st
from llm.base import Chat_model
from utils.messages import UI_messages, Messages_translator
from utils.util import Read_json, Split_and_format_documents, Generate_local_faiss

def Setting_session_state():
    if "RAG_prepare" not in st.session_state:
        st.session_state.RAG_prepare = False
    if "model_prepare" not in st.session_state:
        st.session_state.model_prepare = False
    if "lang_changed" not in st.session_state:
        st.session_state.lang_changed = True
    if "progress" not in st.session_state:
        st.session_state.progress = "start"
    if "diagnosis" not in st.session_state:
        st.session_state.diagnosis = ""
    if "user_input_instance" not in st.session_state:
        st.session_state.user_input_instance = ""
    if "user_data" not in st.session_state:
        st.session_state.user_data = {}
    if "system_messages" not in st.session_state:
        st.session_state.system_messages = {}
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = {}
    if "user_messages" not in st.session_state:
        st.session_state.user_messages = {}
    if "memory" not in st.session_state: #user language로 저장
        st.session_state.memory = [] #[{"role": "ai/user", "content": "something"}]
    if "chat_memory" not in st.session_state: #영어로 저장
        st.session_state.chat_memory = [] #[{"role": "ai/user", "content": "something"}]

def Setting_language():
    if st.session_state.lang_changed == True:
        if "user_language" not in st.session_state:
            ui = UI_messages("english")
        else:
            ui = UI_messages(st.session_state.user_language)
        st.session_state.system_messages = ui.system_messages()
        st.session_state.ai_messages = ui.ai_messages()
        st.session_state.user_messages = ui.user_messages()
        st.session_state.lang_changed = False

def Cache_language_status():
    st.session_state.lang_changed = True


def User_input_below():
    def Submit():
        ulang_2_eng = Messages_translator(st.session_state.user_language, to_eng=True)
        st.session_state.user_input_instance = ulang_2_eng.translate(st.session_state.widget)
        if st.session_state.progress == "information":
            st.session_state.user_data["additional_context_ulang"] = st.session_state.widget
        if st.session_state.progress == "chat":
            st.session_state.user_data["chat_input_ulang"] = st.session_state.widget
        st.session_state.widget = ""
    below_input_bar = st.text_input(
        label=st.session_state.system_messages["send_to_ai"]["request"],
        key="widget",
        on_change=Submit
        )

def Clear():
    col1, col2, col3 = st.columns(3)
    with col3:
        clear_button = st.button(label=st.session_state.system_messages["reset"], use_container_width=True)
    if clear_button:
        st.session_state.progress = "start"
        st.session_state.user_data = {}
        st.session_state.user_input_instance = ""
        st.session_state.memory = []
        st.session_state.chat_memory = []
        st.session_state.diagnosis = ""
        st.rerun()

@st.cache_data(show_spinner="WAIT...")
def Load_chat_model(chosen_llm: str, api_token: str):
    chat_model = Chat_model(chosen_llm, api_token)
    return chat_model

@st.cache_data(show_spinner="WAIT...")
def Prepare_for_RAG(main_path, faiss_path):
    papers_json = Read_json(os.path.join(main_path, "resource", "Entrez_selected_for_RAG.json"))
    abs_list_raw = list(items["abstract"] for items in papers_json["paper_list"])
    metadata_list_raw = list(dict(filter(lambda items: items[0] != "abstract", article_dict.items())) for article_dict in papers_json["paper_list"])
    abs_list, metadata_list = Split_and_format_documents(abs_list_raw, metadata_list_raw)
    Generate_local_faiss(abs_list, metadata_list, faiss_path)

class Format_form:
    form_choices_dict, form_suffix_dict = UI_messages.format_messages_for_form()

    def __init__(self, label:str):
        if self.validate_label(label):
            self.label = label

    def validate_label(self, label: str):
        if label not in self.form_choices_dict:
            raise KeyError("Wrong label")
        else:
            return True
        
    def format_form_options(self):
        label_index = list(self.form_choices_dict.keys()).index(self.label)
        options_list = list(self.form_choices_dict.values())[label_index]
        res_list = list()
        for i in range(len(options_list)):
            res_list.append(str(label_index)+str(i))
        return res_list
    
    def format_form_choices(self, num):
            return st.session_state.system_messages["form"][self.label]["contents"][int(num[1])]

    @classmethod
    def format_form_result(cls, args_list: list):
        label_keys_list = list(cls.form_choices_dict.keys())
        suffix = cls.form_suffix_dict
        text: str = ""
        for item in args_list:
            label_key = label_keys_list[int(item[0])]
            text += suffix[label_key]+" "+cls.form_choices_dict[label_key][int(item[1])]+".\n"
        return text