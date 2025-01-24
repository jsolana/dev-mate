import logging
import os

import requests
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

GITLAB_API_TOKEN = os.environ.get("GITLAB_API_TOKEN")
GITLAB_API_BASE_URL = os.environ.get("GITLAB_API_BASE_URL")
RAG_API_TOKEN = os.environ.get("RAG_API_TOKEN")
RAG_URL = os.environ.get("RAG_URL")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI

app = FastAPI()


@app.post("/issues/webhook")
async def gitlab_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if payload.get("object_kind") == "issue" and payload.get("event_type") == "issue":

        action = payload.get("object_attributes", {}).get("action")

        if action not in ["open", "update"]:
            logger.info(f"Ignoring event with action: {action}")
            return {
                "message": "Event not processed. Only 'open' and 'update' actions are handled."
            }

        project_id = payload.get("project", {}).get("id")
        issue_iid = payload.get("object_attributes", {}).get("iid")
        issue_title = payload.get("object_attributes", {}).get("title")
        description = payload.get("object_attributes", {}).get("description", "")

        logger.info(
            f"Processing issue: {issue_title} (IID: {issue_iid}) in project ID: {project_id}"
        )

        if not (project_id and issue_iid):
            logger.error("Missing project_id or issue_iid in payload")
            raise HTTPException(
                status_code=400, detail="Missing project_id or issue_iid in payload"
            )

        headers = {"Private-Token": GITLAB_API_TOKEN}
        labels_url = f"{GITLAB_API_BASE_URL}/projects/{project_id}/labels"
        logger.info(f"Fetching labels from: {labels_url}")
        labels_response = requests.get(labels_url, headers=headers)
        if labels_response.status_code != 200:
            raise HTTPException(
                status_code=labels_response.status_code, detail="Failed to fetch labels"
            )

        labels = [label["name"] for label in labels_response.json()]

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": RAG_API_TOKEN,
        }

        query = f"""
            Based on the following issue description:
            Description: {description}

            And the available labels in the project: {', '.join(labels)}

            Please suggest the label(s) that best fit this issue, considering its description and the context provided. For your response, use the format: /label ~"label_name". If you believe multiple labels are relevant, include all of them, separated by commas.
            As a fallback use /label ~"Maintenance"
            """

        data = {
            "query": query,
            "system_prompt": "ou are an expert in issue classification, skilled at analyzing problem descriptions and identifying the most relevant labels for a given task. Use your expertise to make the best classification based on the available information.",
            "temperature": 0,
            "context": [],
        }

        response = requests.post(RAG_URL, headers=headers, json=data)
        suggested_labels = '/label ~"Maintenance"'
        if response.status_code == 200:
            response_data = response.json()
            answer = response_data.get("answer")
            if "/label ~" in answer:
                suggested_labels = answer

        query = f"""
            Based on the following issue description:
            Description: {description}

            Provide a helpful comment for the task based on your knowledge to solve it or improve the description.
            """
        data = {
            "query": query,
            "system_prompt": "You are an AI assistant trying to help as much as possible.",
            "temperature": 0,
            "context": [],
        }

        response = requests.post(RAG_URL, headers=headers, json=data)

        if response.status_code == 200:
            response_data = response.json()
            answer = response_data.get("answer")
            if "try a different prompt" not in answer:
                sources = response_data.get("sources", [])
                sources_info = "\n".join(
                    [f"- [{source['name']}]({source['url']})" for source in sources]
                )
                comment_body = f"""{answer}\n\n### Sources\n\n{sources_info}\n\n{suggested_labels}"""
                headers = {"Private-Token": GITLAB_API_TOKEN}
                comment_url = f"{GITLAB_API_BASE_URL}/projects/{project_id}/issues/{issue_iid}/notes"
                comment_data = {"body": comment_body}
                comment_response = requests.post(
                    comment_url, headers=headers, json=comment_data
                )
                if comment_response.status_code != 201:
                    raise HTTPException(
                        status_code=comment_response.status_code,
                        detail="Failed to create comment",
                    )
            else:
                logger.info(f"Ignored response, cause it is not valid: {answer}")
        else:
            print(f"Error: {response.status_code}, {response.text}")

        return {"message": "Webhook processed and comment created successfully"}

    raise HTTPException(status_code=400, detail="Event not handled")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
