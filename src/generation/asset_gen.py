import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.generation.model_factory import get_langchain_model
from src.prompts.code_generation_prompts import ART_PROMPT


def generate_assets(
        gdd_context: str,
        provider: str = "openai",
) -> str:
    """
    Generate the art assets for this specific game using LangChain factory.
    """
    # Use the unified factory to get the correct model for the provider
    llm = get_langchain_model(provider=provider, temperature=0.5)

    prompt = ChatPromptTemplate.from_messages([
        ("system", ART_PROMPT),
        ("user", "GDD Content:\n{gdd}")
    ])

    chain = prompt | llm | StrOutputParser()

    try:
        response = chain.invoke({"gdd": gdd_context})

        # Extract JSON block from the response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return response
    except Exception as e:
        print(f"[AssetGen Error] {e}")
        return "{}"