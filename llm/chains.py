import re
from operator import itemgetter
from langchain.vectorstores.faiss import FAISS
from langchain.schema.runnable import RunnableLambda
from utils.util import embedding_openai

def Add_feature_context(_dict: dict):
    vectordb_RAG = FAISS.load_local(folder_path=_dict["faiss_path"], embeddings=embedding_openai, allow_dangerous_deserialization=True)
    retriever = vectordb_RAG.as_retriever(
        search_type = "similarity",
        search_kwargs= {"k": 3}
        )
    _dict["context"] = [item.page_content for item in retriever.invoke(_dict["query"])]
    del _dict["faiss_path"]
    return _dict
def Add_diagnostic_contexts(_dict: dict) -> dict:
    vectordb_RAG = FAISS.load_local(folder_path=_dict["faiss_path"], embeddings=embedding_openai, allow_dangerous_deserialization=True)
    context_list = vectordb_RAG.similarity_search(query=_dict["formatted_sx"], k=21)
    _dict["context_list"] = [item.page_content for item in context_list]
    del _dict["faiss_path"]
    return _dict
def Add_chat_context(_dict: dict):
    vectordb_RAG = FAISS.load_local(folder_path=_dict["faiss_path"], embeddings=embedding_openai, allow_dangerous_deserialization=True)
    retriever = vectordb_RAG.as_retriever(
        search_type = "similarity_score_threshold",
        search_kwargs= {"k": 3, "score_threshold": 0.3}
        )
    question = _dict["diagnosis"][:600] +"\n==\n"+ _dict["query"]
    _dict["context"] = [item.page_content for item in retriever.invoke(question)]
    del _dict["faiss_path"]
    return _dict


def Activate_diagnosis_chain(
        chat_model,
        main_prompt,
        evaluate_each_prompt,
        diagnose_each_prompt,
        feature_prompt,
        translate_prompt,
        _dict:dict):
    
    def format_symptoms(_dict: dict) -> dict:
        symptom_chain = RunnableLambda(Add_feature_context) | feature_prompt | chat_model
        _dict["formatted_sx"] = symptom_chain.invoke({
            "query": _dict["symptoms"],
            "faiss_path": _dict["faiss_path"]
            }).content
        return _dict
    def map_diagnosis(_dict: dict) -> str:
        def add_score(_dict:dict) -> dict:
            evaluate_each_chain = evaluate_each_prompt | chat_model
            res = evaluate_each_chain.invoke(_dict)
            try:
                score = re.match(r"^\d([.]\d+)?", res.content).group(0)
            except:
                score = "0"
            if float(score) > 0.3:
                res= _dict["context"]+" <SCORE> "+score+"\n"
            else:
                res= "useless"
            return res
        def make_comment(_dict: dict):
            comment_chain = diagnose_each_prompt | chat_model
            comment = comment_chain.invoke(_dict).content
            return comment
        text = ""
        cnt = 0
        above_thr_list = []
        for item in _dict["context_list"]:
            modified_context = add_score({
                "symptoms": _dict["formatted_sx"],
                "context": item
            })
            if modified_context == "useless":
                cnt += 1
            else:
                above_thr_list.append(modified_context)
        text += f"{cnt} of 21 professionals said that the baby could be in a healthy condition. Other professionals said as below."
        for i in range(0, len(above_thr_list), 3):
            joined_context = "\n".join(above_thr_list[i:i+3])
            comment = make_comment({
                "symptoms": _dict["formatted_sx"], 
                "context": joined_context
                })
            text += "\n==\n"+comment
        return text
    
    output_dict = dict()
    diagnosis_chain = {
        "symptoms": itemgetter("symptoms"),
        "comments": RunnableLambda(format_symptoms) | RunnableLambda(Add_diagnostic_contexts) | RunnableLambda(map_diagnosis),
        } | main_prompt | chat_model
    output_dict["english"] = diagnosis_chain.invoke(_dict).content
    korean_chain = translate_prompt | chat_model
    output_dict["user_language"] = korean_chain.invoke({"input": output_dict["english"]}).content
    return output_dict

def Activate_chat_chain(
        chat_model,
        main_prompt,
        translate_prompt,
        _dict):
    output_dict = dict()
    chat_chain = RunnableLambda(Add_chat_context) | main_prompt | chat_model
    output_dict["english"] = chat_chain.invoke(_dict).content
    korean_chain = translate_prompt | chat_model
    output_dict["user_language"] = korean_chain.invoke({"input": output_dict["english"]}).content
    return output_dict
