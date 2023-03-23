import datetime
import requests
import re
import json
from bs4 import BeautifulSoup

class SearchEngine():
    def __init__(self,api_key,search_engine_id):
        self.api_key=api_key
        self.search_engine_id=search_engine_id

    def Search(self,query_text):
        url = f"https://www.googleapis.com/customsearch/v1?key={self.api_key}&cx={self.search_engine_id}&q={query_text}"
        try:
            response = requests.get(url)
            response.raise_for_status()  # 检查响应状态码是否为200
            results = response.json()
            return results
        except requests.exceptions.HTTPError as errh:
            print("HTTP Error:", errh)
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
        except requests.exceptions.RequestException as err:
            print("Something went wrong:", err)

url = "https://github.blog/2023-03-22-github-copilot-x-the-ai-powered-developer-experience/"

def ToFilename(s):
    # 将字符串转换为小写，并将空格替换为下划线
    s = s.lower().replace(" ", "_")
    # 使用正则表达式去除非法字符
    s = re.sub(r"[^\w-]", "", s)
    return s

def GenerateDictoryName(text):
    text=text[:10]
    file_name=ToFilename(text)
    now = datetime.datetime.now()
    dic_name = now.strftime("%Y-%m-%d_%H-%M-%S")
    return file_name+"_"+dic_name

def GetUrlText(url):
    text=""
    success=False
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查响应状态码是否为200
        # 将响应内容解析为BeautifulSoup对象
        soup = BeautifulSoup(response.content, "html.parser")
        # 获取纯文本内容
        text = soup.get_text()
        success=True
    except requests.exceptions.HTTPError as errh:
        print("HTTP Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print("Something went wrong:", err)
    
    lines = [line for line in text.split("\n") if line.strip()]
    # 将行重新组合成字符串
    new_text = "\n".join(lines)
    return new_text,success

def WriteHtmlTextToFile(text,dic_name,file_name,suffix,encoding="utf-8"):
    # 将文本内容写入文件
    if not os.path.exists(dic_name):
        os.makedirs(dic_name)
    final_path=dic_name+"/"+file_name+suffix
    with open(final_path, "w",encoding=encoding) as f:
        f.write(text)
    return final_path

def WriteSearchResultsToPath(dic_name,search_results):
    file_names=[]
    for item in search_results["items"]:
        url=item["link"]
        title=item["title"]
        file_name=ToFilename(title)
        text,success=GetUrlText(url)
        if(success):
            WriteHtmlTextToFile(text,dic_name,file_name,".txt",encoding="utf-8")
            file_names.append(file_name)
    return file_names
        
import os
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import TokenTextSplitter
from langchain.llms import OpenAI
from langchain.chains import ChatVectorDBChain
from langchain.document_loaders import DirectoryLoader
import jieba as jb
from langchain.chat_models import ChatOpenAI

def WriteToCut(dic_name,file_names):
    for file_name in file_names:
        #读取data文件夹中的中文文档
        file_path=dic_name+"/"+file_name+".txt"
        with open(file_path,"r",encoding='utf-8') as f:  
            data = f.read()
        #对中文文档进行分词处理
        cut_data = " ".join([w for w in list(jb.cut(data))])
        #分词处理后的文档保存到data文件夹中的cut子文件夹中
        cut_file=dic_name+"/cut/"+file_name+".txt"
        if not os.path.exists(dic_name+"/cut"):
            os.makedirs(dic_name+"/cut")
        with open(cut_file, 'w',encoding='utf-8') as f:   
            f.write(cut_data)

def AskToGPT(dic_name,question,openai_key):
    #加载文档
    loader = DirectoryLoader(dic_name+"/cut",glob='**/*.txt')
    docs = loader.load()
    #文档切块
    text_splitter = TokenTextSplitter(chunk_size=1000, chunk_overlap=0)
    doc_texts = text_splitter.split_documents(docs)
    #调用openai Embeddings
    os.environ["OPENAI_API_KEY"] = openai_key
    embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    #向量化
    vectordb = Chroma.from_documents(doc_texts, embeddings, persist_directory=dic_name+"/cut")
    vectordb.persist()
    #创建聊天机器人对象chain
    chain = ChatVectorDBChain.from_llm(ChatOpenAI(temperature=1), vectordb, return_source_documents=True)
    def get_answer(question):
        chat_history = []
        result = chain({"question": question, "chat_history": chat_history});
        return result["answer"]
    answer=get_answer(question)
    return answer
   
google_api_key=""
search_engine_id=""
openai_key=""
with open("config.json", "r") as f:
    data = json.load(f)
    openai_key=data["openai_key"]
    google_api_key=data["google_api_key"]
    search_engine_id=data["search_engine_id"]
if(google_api_key==None or google_api_key=="" or search_engine_id==None or search_engine_id=="" or openai_key==None or openai_key==""):
    print("please config api")
else:
    engine=SearchEngine(google_api_key,search_engine_id)
    while(1):
        print("ask sth:")
        search_text=input()
        search_result=engine.Search(search_text)
        dic_name = GenerateDictoryName(search_text)
        file_names=WriteSearchResultsToPath(dic_name,search_result)
        WriteToCut(dic_name,file_names)
        print(AskToGPT(dic_name,search_text,openai_key))




    