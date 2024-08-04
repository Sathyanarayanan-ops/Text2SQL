import os
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import re

os.environ["GROQ_API_KEY"] = "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"
db = SQLDatabase.from_uri("sqlite:///Chinook.db")
llm = ChatGroq(model="llama3-8b-8192")
execute_query = QuerySQLDataBaseTool(db=db)

def extract_sql_query(text):
    match = re.search(r'SELECT.*', text, re.IGNORECASE | re.DOTALL)
    return match.group(0) if match else text

write_query = create_sql_query_chain(llm, db) | extract_sql_query

answer_prompt = PromptTemplate.from_template(
"""Given the following user question, corresponding SQL query, and SQL result, answer the user question
Question: {question}
SQL Query: {query}
SQL Result: {result}
Answer:"""
)

answer = answer_prompt | llm | StrOutputParser()

chain = (
    RunnablePassthrough.assign(query=write_query).assign(
        result=lambda x: execute_query.run(x['query'])
    )
    | answer
)

question = "How many employees are there"
response = chain.invoke({"question": question})
print(response)

st.title("Text to SQL")
