import os
import sys
from pathlib import Path
import datetime

from dotenv import load_dotenv
from google.adk.agents import Agent, LoopAgent
from google.adk.tools import agent_tool

load_dotenv()

MODEL = os.getenv("MODEL", "gemini-flash-latest")
blog_planner = Agent(
    name="BlogPlanner",
    model= MODEL,
    description="Create a practical, skimmable outline in Markdown.",
    instruction="""You are a technical content strategist. Produce clear Markdown outline with:
    - Title
    - Short Intro
    - 4-6 main sections
    - conclusion
    
    If 'codebase_context' exists in state, weave in specifc sections/snippets.
    Return only the outline in Markdown""",
    output_key="blog_outline",
)

class OutlineValidationChecker(Agent):
    def __init__(self):
        super().__init__(
            name="OutlineValidationChecker",
            model=MODEL,
            description="Validate the outline is usable.",
            instruction="""Check the outline in state 'blog_outline'. If it has a title, intro, 4-6 sections ad a conclusion, respnd exactly "ok".
            Otherwise response exactly "retry" and list missing pieces.""",
            output_key="validation_result",
        )

robust_plog_planner = LoopAgent(
    name = "RobustBlogPlanner",
    description = "Retries planning if valiadtion fails.",
    sub_agents = [blog_planner, OutlineValidationChecker()],
    max_iterations = 3,
)

blog_writer = Agent(
    name="BlogWriter",
    model=MODEL,
    description="Write a technical blog post from an outline.",
    instruction="""Write a complete Markdown article from the outline in 'blog_outline'.
    Guidelines:
    - Audience: Software engineers, skip basics and focus on practical insights.
    - Explain both 'how' and 'why'.
    - Include consice code snippets when helpful.
    - Follow the outline structure(H2, H3)
    - Output only the final article in Markdown (no fence around the whole post).""",
    output_key="blog_post")

class BlogPostValidationChecker(Agent):
    def __init__(self):
        super().__init__(
            name="BlogPostValidationChecker",
            model=MODEL,
            description="Validate the blog post is usable.",
            instruction="""Check the blog post in state 'blog_post'. If it has a title, intro, 4-6 sections matching the outline and a conclusion and technical clarity, respnd exactly 'ok'.
            Otherwise response exactly "retry" with specific fixes.""",
            output_key="validation_result"
        )

robust_blog_writer = LoopAgent(
    name = "RobustBlogWriter",
    description = "Retries writing if valiadtion fails.",
    sub_agents = [blog_writer, BlogPostValidationChecker()],
    max_iterations = 3,
)

planner_tool = agent_tool.AgentTool(agent=robust_plog_planner)
writer_tool = agent_tool.AgentTool(agent=robust_blog_writer)

root_agent = Agent(
    name="blogger",
    model=MODEL,
    description="Minimal multi agent blogger that plans and writes.",
    instruction=f"""
    if the use gives a topic:
        1) Call the planner tool to create an outline.
        2) Call the writer tool to write a blog post from the outline.
        3) End with 3 alternate titles and 2 tweet length hooks.
    if the trends tool fails or times out, continue with a sensible draft and outlineanyway.
    Date: {datetime.datetime.now().strftime("%Y-%m-%d")} """,
    tools=[planner_tool, writer_tool])