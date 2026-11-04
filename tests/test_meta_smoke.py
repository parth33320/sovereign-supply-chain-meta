import os
from langchain_openai import ChatOpenAI

import pytest

def test_meta_smoke():
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        pytest.skip("META_API_KEY not set; skipping live Meta API smoke test")

    llm = ChatOpenAI(
        model=os.environ.get("META_MODEL_NAME", "muse-spark-1.3"),
        api_key=api_key,
        base_url=os.environ.get("META_API_BASE_URL"),
        temperature=0
    )
    response = llm.invoke("ping")
    print(f"Meta client response: {response.content}")
    assert response.content is not None
    assert isinstance(response.content, str)
    assert len(response.content.strip()) > 0

if __name__ == "__main__":
    test_meta_smoke()
    print("Smoke test passed successfully!")
