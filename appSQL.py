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
import tempfile

# Set up environment and LLM
os.environ["GROQ_API_KEY"] = "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"
llm = ChatGroq(model="llama3-8b-8192")

# Function to extract SQL query
def extract_sql_query(text):
    match = re.search(r'SELECT.*', text, re.IGNORECASE | re.DOTALL)
    return match.group(0) if match else text

# Streamlit UI
st.title("Text to SQL Chat")

# File uploader
uploaded_file = st.file_uploader("Choose a SQLite database file", type=["db"])

if uploaded_file:
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        db_path = tmp_file.name

    # Connect to the uploaded database
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
    
    # Set up the chain
    execute_query = QuerySQLDataBaseTool(db=db)
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

    # Chat interface
    st.subheader("Chat with your database")
    user_question = st.text_input("Ask a question about your database:")
    
    if user_question:
        with st.spinner("Generating response..."):
            response = chain.invoke({"question": user_question})
        st.write(response)

else:
    st.info("Please upload a SQLite database file to begin.")

# Clean up the temporary file
if 'db_path' in locals():
    os.unlink(db_path)