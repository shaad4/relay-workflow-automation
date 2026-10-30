import asyncio
import os

from mcp import Client
from server import mcp


WORKFLOW_ID = "6d4c5e88-2ffa-4f7e-97f8-45a272f785a4"


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "relay_update_node",
            {
                "workflow_id": WORKFLOW_ID,
                "version": 1,
                "node_id": "generate_1",
                "configuration": {
                    "connection_id": os.environ["RELAY_AI_CONNECTION_ID"],
                    "model": os.environ["RELAY_AI_MODEL"],
                    "instructions": (
                        "You are an academic report assistant. "
                        "Generate accurate student grade reports. "
                        "Calculate the total and percentage from the "
                        "provided marks. Use this grading scale: "
                        "A = 90-100, B = 80-89, C = 70-79, "
                        "D = 60-69, F = below 60. "
                        "Do not invent student data."
                    ),
                    "prompt": (
                        "Generate a grade report for:\n"
                        "Student: {{trigger.data.student_name}}\n"
                        "Maths: {{trigger.data.maths}}\n"
                        "Science: {{trigger.data.science}}\n"
                        "English: {{trigger.data.english}}\n\n"
                        "Each subject is out of 100. "
                        "Include total marks out of 300, "
                        "percentage, overall grade, and "
                        "a short performance summary."
                    ),
                },
            },
        )

        assert not result.is_error, result

        print("AI Generate node updated successfully!")

        for block in result.content:
            if block.type == "text":
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())