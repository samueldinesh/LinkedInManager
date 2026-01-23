
import os
import asyncio
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.WARNING)

async def test_retry_behavior():
    print("Testing ChatGoogleGenerativeAI retry behavior...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return

    # Initialize with max_retries=0 (should fail immediately)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", # Known to have 0 quota
        google_api_key=api_key,
        max_retries=0, 
        transport="rest"
    )

    print("Invoking model with max_retries=0...")
    try:
        await llm.ainvoke("Test")
    except Exception as e:
        print(f"Caught expected exception: {type(e).__name__}: {e}")

    # Initialize with max_retries=1
    llm2 = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=api_key,
        max_retries=1
    )

    print("\nInvoking model with max_retries=1...")
    try:
        await llm2.ainvoke("Test")
    except Exception as e:
        print(f"Caught expected exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_retry_behavior())
