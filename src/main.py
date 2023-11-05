import os
import re
from json import loads, JSONDecodeError
from datetime import datetime
from collections import defaultdict

import pymongo
from pymongo.database import Database
from pymongo.errors import InvalidId

from bson.objectid import ObjectId

from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from sanic import Sanic, Request
from sanic.log import logger
from sanic.response import HTTPResponse, html, redirect, text, json, file, empty
from sanic.exceptions import NotFound

from dotenv import dotenv_values


app = Sanic(name="turvalisus")
static_directory = os.path.abspath("static")

ALLOW_UNAUTHORISED = ["main", "statistics"]

env = Environment(
    loader=FileSystemLoader(os.path.abspath("templates")),
    autoescape=select_autoescape(["jinja"]),
)

turvalisus_db: Database


def get_language(req: Request):
    language = req.cookies.get("user_language", None)
    if language in supported_languages:
        return language

    accepted_languages = req.headers.get("Accept-Language", "en").split(",")
    for lang in accepted_languages:
        if lang[:2] in supported_languages:
            return lang[:2]

    return "en"


@app.exception(NotFound)
async def page_not_found(request, exception):
    return html(
        "<h2>There is nothing here</h2>\n<a href='/'>Return to the homepage</a>"
    )


@app.route("/")
async def home(request: Request):
    if request.cookies.get("token", None) is not None:
        return redirect("/select/collections")
    language = get_language(request)

    return redirect(f"/main/welcome")


@app.route("/<req_template>/<req_content>")
async def build_page(request: Request, req_template, req_content):
    try:
        template = env.get_template(f"{req_template}.html.jinja")
    except TemplateNotFound:
        raise NotFound

    language = get_language(request)

    user_token = request.cookies.get("token", None)
    if user_token is None and req_template not in ALLOW_UNAUTHORISED:
        return redirect(f"/main/welcome")

    locale = turvalisus_db.get_collection("locale").find_one(
        {"lang": language, "collection": req_template}
    )

    content = turvalisus_db.get_collection("content").find_one(
        {"$or": [{"lang": language}, {"lang": {"$exists": False}}], "page": req_content}
    )

    content = {} if content is None else content

    return html(template.render({"content": content, "locale": locale}))


@app.route("/task/all", ["GET"])
async def get_all_tasks(request: Request):
    user_token = request.cookies.get("token", None)
    if user_token is None:
        return empty(401)
    if ObjectId(user_token) not in turvalisus_db.get_collection("users").distinct(
        "_id"
    ):
        return empty(401)

    language = get_language(request)

    user = turvalisus_db.get_collection("users").find_one({"_id": ObjectId(user_token)})
    user_completed_pages = [answer["page"] for answer in user["answers"]]

    task_pages = turvalisus_db.get_collection("content").find(
        {"lang": language, "task": {"$exists": True}}
    )

    available_pages = defaultdict(lambda: {"amount": 0, "available": []})
    for page in task_pages:
        if page["page"] not in user_completed_pages:
            available_pages[page["collection"]]["id"] = page["collection"]
            available_pages[page["collection"]]["available"].append(page["page"])
            available_pages[page["collection"]]["amount"] += 1

    return json(list(available_pages.values()))


@app.route("/task/submit", ["POST"])
async def submit_task(request: Request):
    user_token = request.cookies.get("token", None)
    if user_token is None:
        return empty(401)
    if ObjectId(user_token) not in turvalisus_db.get_collection("users").distinct(
        "_id"
    ):
        return empty(401)

    user = turvalisus_db.get_collection("users").find_one({"_id": ObjectId(user_token)})

    if "exited" in user:
        return empty(401)

    page_submitted = request.args.get("page", "")
    if page_submitted == "" or page_submitted in [
        answer["page"] for answer in user["answers"]
    ]:
        return empty(400)

    language = get_language(request)

    page = turvalisus_db.get_collection("content").find_one(
        {"page": page_submitted, "lang": language}
    )
    if page is None:
        return empty(404)
    answers = page["answers"]

    question_is_quiz = request.args.get("quiz", False)

    if question_is_quiz:
        user_answers = request.args.get("option", [])
        try:
            user_answers = loads(user_answers)
        except JSONDecodeError:
            return empty(400)
        if len(user_answers) != len(answers) or None in user_answers:
            return empty(400)

        results = []
        score = 0
        for ans, user_ans in zip(answers, user_answers):
            results.append(ans[user_ans])
            score += ans[user_ans]

        turvalisus_db.get_collection("users").update_one(
            {"_id": ObjectId(user_token)},
            {
                "$inc": {"points": score},
                "$push": {"answers": {"page": page_submitted, "quiz": user_answers}},
            },
        )

        return json(results)

    else:
        option_submitted = request.args.get("option", "0")
        if not option_submitted.isnumeric() or int(option_submitted) + 1 > len(answers):
            return empty(400)
        option_submitted = int(option_submitted)

        turvalisus_db.get_collection("users").update_one(
            {"_id": ObjectId(user_token)},
            {
                "$inc": {"points": answers[option_submitted]["points"]},
                "$push": {
                    "answers": {"page": page_submitted, "option": option_submitted}
                },
            },
        )

        return json(answers[option_submitted])


@app.route("/user/create", ["POST"])
async def create_user(request: Request):
    if request.cookies.get("token", None) is not None:
        return text("WUSEREXISTS")

    nickname = request.args.get("nickname", "")

    if re.fullmatch("^(?:[a-zA-Z0-9]| (?=[^ ]*$)){2,20}$", nickname) is None:
        return text("EILLEGALNAME")

    user_id = (
        turvalisus_db.get_collection("users")
        .insert_one(
            {
                "nickname": nickname,
                "created": datetime.now(),
                "points": 0,
                "answers": [],
            }
        )
        .inserted_id.__str__()
    )

    response = text("ok")
    response.cookies["token"] = user_id

    return response


@app.route("/user/nickname", ["GET"])
async def get_nickname(request: Request):
    user_id = request.cookies.get("token", None)
    if user_id is None:
        return empty(401)

    user_entry = turvalisus_db.get_collection("users").find_one(
        {"_id": ObjectId(user_id)}
    )
    if user_entry is None:
        return empty(404)

    return text(user_entry.get("nickname", None))


@app.route("/user/points", ["GET"])
async def get_points(request: Request):
    user_id = request.cookies.get("token", None)
    if user_id is None:
        return empty(401)

    user_entry = turvalisus_db.get_collection("users").find_one(
        {"_id": ObjectId(user_id)}
    )
    if user_entry is None:
        return empty(404)

    return text(str(user_entry.get("points", None)))


@app.route("/user/logout", ["POST"])
async def logout(request: Request):
    user_id = request.cookies.get("token", None)
    if user_id is None:
        return text("WNOUSER", 200)

    try:
        turvalisus_db.get_collection("users").update_one(
            {"_id": ObjectId(user_id), "exited": {"$exists": False}},
            {
                "$set": {"exited": datetime.now()},
                "$inc": {"points": 10},
            },
        )
    except InvalidId:
        return text("EINVALIDTOKEN", 400)

    response = text("ok", 200)
    del response.cookies["token"]

    return response


@app.route("/api/languages", ["GET"])
async def get_supported_languages(_: Request):
    return json(supported_languages, 200)


@app.route("/api/statistics", ["GET"])
async def get_statistics_data(request: Request):
    user_score = request.args.get("compare", None)
    if user_score is None or not user_score.isnumeric():
        return empty(400)

    user_score = int(user_score)

    language = get_language(request)

    points_statistics = (
        turvalisus_db.get_collection("content")
        .aggregate(
            [
                {"$match": {"$or": [{"lang": language}, {"lang": {"$exists": False}}]}},
                {"$group": {"_id": None, "points_sum": {"$sum": "$max_points"}}},
            ]
        )
        .next()
    )

    users_per_score = list(
        turvalisus_db.get_collection("users").aggregate(
            [{"$group": {"_id": "$points", "count": {"$sum": 1}}}]
        )
    )

    users_count = turvalisus_db.get_collection("users").count_documents({}) or 1

    user_better_than = 0
    for entry in users_per_score:
        if entry["_id"] < user_score:
            user_better_than += entry["count"]

    users_exited = round(
        (
            turvalisus_db.get_collection("users").count_documents(
                {"exited": {"$exists": True}}
            )
            / users_count
        )
        * 100
    )

    return json(
        {
            "maximum": points_statistics["points_sum"] + 10,
            "comparison": round((user_better_than / users_count) * 100),
            "exited": users_exited,
        }
    )


@app.route("/settings/consent", ["POST"])
async def set_cookies_consent(_: Request):
    response = text("")
    response.cookies["consent"] = "true"
    response.body = "ok"
    return response


@app.route("/settings/language", ["POST"])
async def set_language(request: Request):
    language = request.args.get("lang", None)
    response = text("")
    if language in supported_languages:
        response.cookies["user_language"] = language
        response.status = 200
    else:
        response.status = 400
    return response


@app.route("/static/<file_name>")
async def serve_static(_, file_name):
    file_path = f"{static_directory}/{file_name}"
    if os.path.exists(file_path):
        return await file(file_path)
    return empty(404)


if __name__ == "__main__":
    env_vars = dotenv_values()

    client = pymongo.MongoClient(
        f"mongodb+srv://{env_vars['MONGO_USERNAME']}:"
        f"{env_vars['MONGO_PASSWORD']}@"
        f"{env_vars['MONGO_HOST']}/"
        f"turvalisus?retryWrites=true&w=majority"
    )

    turvalisus_db = client.turvalisus

    logger.info(f"Database connection established")

    supported_languages = turvalisus_db.locale.distinct("lang")

    app.run(port=8080, host="0.0.0.0")
