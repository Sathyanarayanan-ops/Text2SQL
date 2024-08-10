import os
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.prompts import PromptTemplate,FewShotPromptTemplate
from langchain_groq import ChatGroq
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import re
import tempfile

os.environ["GROQ_API_KEY"] = ""
llm = ChatGroq(model="llama3-8b-8192")


import re

# def extract_sql_queries(text):
#     queries = []
#     matches = re.findall(r'SELECT.*?;', text, re.IGNORECASE | re.DOTALL)
#     for match in matches:
#         query = match.strip(';')
#         queries.append(query)
#     return queries



examples = [
    {
        "input": "Show the average rating and number of reviews for each restaurant, but only for those with more than 10 reviews.",
        "query": "SELECT r.restaurant_name, AVG(rv.rating) AS avg_rating, COUNT(rv.review_id) AS review_count FROM restaurants r JOIN reviews rv ON r.restaurant_id = rv.restaurant_id GROUP BY r.restaurant_id HAVING review_count > 10 ORDER BY avg_rating DESC;",
        "SQLResult": "[('Gourmet Delight', 4.8, 15), ('Tasty Bites', 4.5, 22), ('Spice Palace', 4.2, 18)]",
        "Answer": "The results show 3 restaurants with more than 10 reviews. Gourmet Delight has the highest average rating of 4.8 with 15 reviews, followed by Tasty Bites with 4.5 and 22 reviews, and Spice Palace with 4.2 and 18 reviews."
    },
    {
        "input": "What are the top 5 customers by total order value?",
        "query": "SELECT c.customer_name, SUM(o.total_amount) AS total_value FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id ORDER BY total_value DESC LIMIT 5;",
        "SQLResult": "[('John Doe', 5000.50), ('Jane Smith', 4500.75), ('Mike Johnson', 4200.25), ('Emily Brown', 3800.00), ('David Lee', 3500.50)]",
        "Answer": "The top 5 customers by total order value are: 1. John Doe ($5000.50), 2. Jane Smith ($4500.75), 3. Mike Johnson ($4200.25), 4. Emily Brown ($3800.00), and 5. David Lee ($3500.50)."
    },
    {
        "input": "Show all items sorted by price.",
        "query": "SELECT * FROM items ORDER BY price;",
        "SQLResult": "[(1, 'Pencil', 0.50), (2, 'Eraser', 1.00), (3, 'Notebook', 3.50), (4, 'Backpack', 25.00), (5, 'Laptop', 800.00)]",
        "Answer": "The items sorted by price from lowest to highest are: Pencil ($0.50), Eraser ($1.00), Notebook ($3.50), Backpack ($25.00), and Laptop ($800.00)."
    },
    {
        "input": "How many accidents happened?",
        "query": "SELECT COUNT(*) FROM accidents;",
        "SQLResult": "[(150,)]",
        "Answer": "There were 150 accidents recorded."
    },
    {
        "input": "What is the average age of users?",
        "query": "SELECT AVG(age) FROM users;",
        "SQLResult": "[(32.5,)]",
        "Answer": "The average age of users is 32.5 years."
    },
    {
        "input": "List the top 5 products by sales.",
        "query": "SELECT product_name, SUM(quantity) as total_sales FROM sales JOIN products ON sales.product_id = products.id GROUP BY product_id ORDER BY total_sales DESC LIMIT 5;",
        "SQLResult": "[('iPhone', 1500), ('Samsung TV', 1200), ('Nike Shoes', 1000), ('PlayStation 5', 800), ('AirPods', 750)]",
        "Answer": "The top 5 products by sales are: 1. iPhone (1500 units), 2. Samsung TV (1200 units), 3. Nike Shoes (1000 units), 4. PlayStation 5 (800 units), and 5. AirPods (750 units)."
    },
    {
        "input": "List the products that have never been ordered.",
        "query": "SELECT p.product_name FROM products p LEFT JOIN order_items oi ON p.product_id = oi.product_id WHERE oi.order_id IS NULL;",
        "SQLResult": "[('Floppy Disk',), ('VHS Player',), ('Walkman',)]",
        "Answer": "The products that have never been ordered are: Floppy Disk, VHS Player, and Walkman."
    }
]





example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")
prompt = FewShotPromptTemplate(
    examples = examples,
    example_prompt = example_prompt,
    prefix = "You are a SQL expert. Given an input question, create a syntactically correct SQL query to run. Unless otherwise specificed, do not return more than {top_k} rows.\n\nHere is the relevant table info: {table_info}\n\nBelow are a number of examples of questions and their corresponding SQL queries.",
    suffix="User input: {input}\nSQL query: ",
    input_variables=["input", "top_k", "table_info"],
)

st.title("Text to SQL Chat")
uploaded_file = st.file_uploader("Choose a SQLite database file", type=["db"])




if uploaded_file:

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        db_path = tmp_file.name


    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
    execute_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm,db,prompt) #| extract_sql_queries

    #chain = write_query | execute_query


    answer_prompt = PromptTemplate.from_template(
            """Given the following user question, corresponding SQL query, and SQL result, answer the user question.
    
            Question: {question}
            SQL Query: {query}
            SQL Result: {result}
            Answer:"""
        )

    answer = answer_prompt | llm | StrOutputParser()

    chain = (
        RunnablePassthrough.assign(query=write_query)
        .assign(result=lambda x: list(execute_query.run(x["query"][0])))
        | answer
)

#     chain = (
#     RunnablePassthrough.assign(query = write_query).assign(
#         result = itemgetter("query") | execute_query
#     )
#     | answer
# )
        

    # for the task that we had , agents seem like a more viable option as described in the langchain docs

    st.subheader("Chat with your database")
    user_question = st.text_input("Ask a question about your database:")
        
    if user_question:
        with st.spinner("Generating response..."):
            response = chain.invoke({"question": user_question, "input": user_question,"top_k":5,"table_info": db.get_table_info()})
        st.write(response)
else:
    st.info("Please upload a SQLite database file to begin")


#clean up the temp file 

if 'db_path' in locals():
    os.unlink(db_path)
