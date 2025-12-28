from smolagents import CodeAgent, DuckDuckGoSearchTool, OpenAIModel
import os
from dotenv import load_dotenv

load_dotenv(override=True)

model = OpenAIModel(
    model_id="gpt-oss-20b",
    api_base="https://llamactl.nmsny.dev/v1",
    api_key=os.environ["LLAMACTL_API_KEY"],
)

agent = CodeAgent(
    tools=[DuckDuckGoSearchTool()],
    model=model,
)


# Run the agent with a task
result = agent.run("What is the current weather in Paris?")
print(result)