import hashlib
import json
import string
import time
import random
import os
import datetime
import uuid
import requests
from data_generation.data_snapshot.base import (
    ConfigDefine,
    get_save_config,
    SAVE_DATA_CONFIG_PG_EE_REPORT,
    SAVE_DATA_CONFIG_PG_EE_PROJECT,
    save_data_path,
    SAVE_DATA_CONFIG_TRINO_AE,
)
from data_generation.data_snapshot.pg_snapshot_helper import (
    import_pg_data,
    check_pg_data,
    export_pg_data,
)
from data_generation.data_snapshot.trino_helper import (
    export_trino_data,
    import_trino_data,
)
from data_generation.db import get_db_session
from urllib.parse import urlparse
from urllib.parse import parse_qs


def sleep(n_secs):
    time.sleep(n_secs)


def record_touched_api(url):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    touched_api_file = f"{base_dir}/touched_api"
    touched_api = {"/user/login"}
    if os.path.exists(touched_api_file):
        with open(touched_api_file, "r") as f:
            touched_api = set(f.read().split("\n"))
    touched_api.add(url)
    with open(touched_api_file, "w") as f:
        f.write("\n".join(touched_api))


def get_token():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    base_url = os.getenv("EE_BASE_URL")
    token_file = f"{base_dir}/token"
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read()
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
        }
        response = requests.post(
            f"{base_url}/tag/getTagTree", json={"params": ["zh"]}, headers=headers
        )
        if response.status_code == 200:
            return token
    token = requests.post(
        f"{base_url}/user/login",
        data={"params": [os.getenv("USERNAME"), os.getenv("PASSWORD")]},
    ).json()["token"]
    with open(token_file, "w") as f:
        f.write(token)
    return token


def before_request(request):
    headers = request.get("headers", {})
    token = get_token()
    headers["authorization"] = f"Bearer {token}"
    record_touched_api(request.get("url"))


def parse_url(url, key):
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query)[key][0]


def sign(request):
    app_id = os.getenv("APP_ID")
    app_secret = os.getenv("APP_SECRET")
    nonce = generate_nonce()
    record_touched_api(request.get("url"))
    request_body = request.get("req_json", {})
    request_body["appid"] = app_id
    request_body["nonce_str"] = nonce

    key_value_list = []
    filtered_dict = {}
    for (key, value) in request_body.items():
        if value is not None and key != "sign":
            filtered_dict[key] = value
            key_value_list.append(
                key
                + "="
                + (
                    type(value) == str
                    and value
                    or json.dumps(value, separators=(",", ":"))
                )
            )

    to_encode_str = "&".join(sorted(key_value_list))

    to_encode_str = to_encode_str + "&key=" + app_secret
    m = hashlib.md5()

    m.update(to_encode_str.encode("utf-8"))

    request["req_json"] = filtered_dict

    request.get("req_json")["sign"] = m.hexdigest().upper()


def generate_nonce():
    return "".join(random.sample(string.ascii_letters, 32))


def current_date():
    today = datetime.date.today()
    return datetime.datetime.strftime(today, "%Y-%m-%d")


def current_timestamp():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d-%H-%M-%S-%f")


def current_isotime():
    now = datetime.datetime.now().isoformat()
    return now


unitOfTime_list = ["day", "week", "month", "quarter", "year"]
efficiency_list = [
    "commit_num",
    "function_num",
    "loc",
    "loc_add_line",
    "loc_delete_line",
    "share_loc",
    "developer_num",
    "dev_equivalent",
    "dev_value_every_share_loc",
    "dev_value_every_share_commit",
    "dev_value_robustness",
    "dev_equivalent_every_developer",
    "cyclomatic_diff",
]
quality_list = [
    "doc_coverage_function_num",
    "issue_blocker_num",
    "issue_critical_num",
    "issue_num",
    "issue_blocker_rate",
    "issue_critical_rate",
    "issue_info_rate",
    "issue_major_rate",
    "issue_minor_rate",
    "function_depend",
    "duplicate_function_num",
    "dryness",
    "modularity",
    "git_tag_number",
    "package_depend",
    "cyclomatic_total",
    "cyclomatic_total_every_function",
]


def get_randomValue(listName):
    if "unitOfTime_list" == listName:
        return random.choice(unitOfTime_list)
    if "efficiency_list" == listName:
        return random.choice(efficiency_list)
    if "quality_list" == listName:
        return random.choice(quality_list)
    return None


def current_time():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_digital_timestamp():
    return int(round(time.time() * 1000))


def eval_value(strings):
    return eval(strings)


def execute_sql(sql):
    with get_db_session() as session:
        session.execute(sql)
        session.commit()


def query_one_from_db(query, column):
    with get_db_session() as session:
        raw_result = session.execute(query).fetchone()
        if raw_result is not None:
            result = dict(raw_result)
        else:
            return None
        if column:
            return str(result[column])
        else:
            return result


def query_all_from_db(query, column):
    with get_db_session() as session:
        results = [dict(r) for r in session.execute(query).fetchall()]
    if column:
        return [str(d[column]) for d in results]
    else:
        return results


def clean_data():
    execute_sql(
        "DELETE FROM report_config_tag_evidence_user_tag WHERE tag_id in (SELECT id FROM report_config_tag WHERE name like 'tag_20%')"
    )

    execute_sql(
        "DELETE FROM report_config_tag WHERE id in (SELECT id FROM report_config_tag WHERE name like 'tag_20%')"
    )

    execute_sql(
        "DELETE FROM team_user_role WHERE project_group_id in (SELECT id FROM project_group WHERE name LIKE 'project_group_20%')"
    )

    execute_sql(
        "DELETE FROM squad_project WHERE project_group_id in (SELECT id FROM project_group WHERE name LIKE 'project_group_20%')"
    )

    execute_sql("DELETE FROM project_group WHERE name LIKE 'project_group_20%'")

    execute_sql(
        "UPDATE commit_authors SET contributor_id=null WHERE name like 'team_user_20%'"
    )
    execute_sql("DELETE FROM contributors  WHERE name like 'team_user_20%'")
    execute_sql(
        "DELETE FROM team_user_role WHERE team_user_id in (SELECT id FROM team_user WHERE name like 'team_user_20%')"
    )
    execute_sql(
        "DELETE FROM team_user_watch_squad WHERE squad_id in (SELECT id FROM squad WHERE name like 'squad_20%')"
    )
    execute_sql(
        "DELETE FROM team_user_watch_squad WHERE squad_id in (SELECT id FROM squad WHERE name like 'department_20%')"
    )
    execute_sql(
        "DELETE FROM team_user_squad_version WHERE squad_id in (SELECT id FROM squad WHERE name like 'squad_20%')"
    )
    execute_sql(
        "DELETE FROM team_user_squad_version WHERE squad_id in (SELECT id FROM squad WHERE name like 'department_20%')"
    )
    execute_sql(
        "DELETE FROM team_user_squad_version WHERE team_user_id in (SELECT id FROM team_user WHERE name like 'team_user_20%')"
    )
    execute_sql(
        "DELETE FROM team_user_tag_version WHERE team_user_id in (SELECT id FROM team_user WHERE name like 'team_user_20%')"
    )
    execute_sql("DELETE FROM team_user WHERE name like 'team_user_20%'")
    execute_sql("DELETE FROM users WHERE primary_email like 'team_user_20%'")

    execute_sql(
        "DELETE FROM squad_project where squad_id in (SELECT id FROM squad WHERE name like 'squad_20%')"
    )

    execute_sql(
        "DELETE FROM squad WHERE id in (SELECT id FROM squad WHERE name like 'squad_20%')"
    )

    execute_sql(
        "DELETE FROM squad_project where squad_id in (SELECT id FROM squad WHERE name like 'department_20%')"
    )

    execute_sql(
        "DELETE FROM squad WHERE id in (SELECT id FROM squad WHERE name like 'department_20%')"
    )

    execute_sql(
        "DELETE FROM role WHERE id in (SELECT id FROM role WHERE name like 'role_20%')"
    )

    execute_sql(
        "DELETE FROM team_subscription WHERE project_id IN (SELECT id FROM projects WHERE project_name LIKE 'merico-mock/ee/project-%')"
    )

    execute_sql(
        "UPDATE projects SET readiness='NOT_INIT' WHERE id in (SELECT id FROM projects WHERE project_name like 'merico-mock/ee/project-%')"
    )
    # delete filters
    execute_sql("UPDATE filters SET is_delete=TRUE WHERE name LIKE 'filters20%';")

    # delete filter conditions
    execute_sql(
        "UPDATE filter_conditions SET is_delete=TRUE WHERE name LIKE 'conditions20%';"
    )


def sum(*args):
    total = 0
    for arg in args:
        total += arg
    return total


def new_uuid():
    return str(uuid.uuid1())


def update_value_by_key(src, key, value):
    src[key] = value
    return src


def get_value_by_key(src, key):
    return src[key]


def find_option_by_desc(options, desc):
    for option in options:
        if option["description"] == desc:
            return option
    return None


def update_option_by_desc(options, desc, value):
    for option in options:
        if option["description"] == desc:
            option.update(value)
    return options


def add_options(squad_member_tag, name):
    options = squad_member_tag["tagOptions"]
    total = 0  # 统计启用的选项数量
    max_id = 0  # 找到当前最大的id
    enable_option = {}  # 启用的选项id
    for option in options:
        if not option["disabled"]:
            total += 1
            if option["tagValue"] > 0:
                enable_option = option
        max_id = max(max_id, option["tagValue"])
    next_id = max_id + 1

    if total >= 20:
        # 如果启用的选项等于20,需要先禁用一个
        enable_option["disabled"] = True
    # 新选项的值
    new_option = {"tagValue": next_id, "description": name, "disabled": False}
    options.append(new_option)
    return squad_member_tag


def import_db_data(project_id):
    team_id = query_one_from_db(
        f"SELECT team_id from team_subscription WHERE project_id='{project_id}'",
        "team_id",
    )
    project = query_one_from_db(f"SELECT * from projects WHERE id='{project_id}'", "")
    report_id = str(project["latest_report_id"])
    if project["incoming_report_id"]:
        report_id = str(project["incoming_report_id"])

    pg_config1: ConfigDefine = get_save_config(SAVE_DATA_CONFIG_PG_EE_REPORT)
    import_pg_data(
        "https://gitee.com/CloudWise/fly-fish.git",
        pg_config1,
        "b3727e99-555d-4f35-815f-b96886d071aa",
        report_id,
        outer_params={"project_id": project_id},
    )

    pg_config2: ConfigDefine = get_save_config(SAVE_DATA_CONFIG_PG_EE_PROJECT)
    import_pg_data(
        "https://gitee.com/CloudWise/fly-fish.git",
        pg_config2,
        "2583d35b-838f-4852-b08d-79732c28b72a",
        project_id,
        outer_params={"team_id": team_id},
    )

    analysis_id = "b3801188-f2c8-4e7f-b2c4-40995e16d313"
    execute_sql(
        f"""
    insert into commit_authors (email, name, team_id)
SELECT DISTINCT ON (author_email) author_email AS email, author_name AS name, s.team_id
FROM project_commit
INNER JOIN team_subscription s ON s.project_id=project_commit.project_id
WHERE project_commit.project_id='{project_id}'
ORDER BY author_email, author_timestamp DESC
ON CONFLICT DO NOTHING;
REFRESH MATERIALIZED VIEW CONCURRENTLY email_to_primary_email_booster;"""
    )
    execute_sql(
        f"UPDATE projects SET latest_report_id='{report_id}' WHERE id='{project_id}'"
    )
    execute_sql(
        f"UPDATE project_commit_value SET latest_report_id='{report_id}' WHERE project_id='{project_id}'"
    )
    execute_sql(
        f"UPDATE function_metrics SET report_id='{report_id}' where project_id='{project_id}'"
    )
    execute_sql(
        f"UPDATE project_report_state SET analysis_id='{analysis_id}' WHERE report_id='{report_id}' AND project_id='{project_id}'"
    )
    trino_config: ConfigDefine = get_save_config(SAVE_DATA_CONFIG_TRINO_AE)
    import_trino_data(
        "https://gitee.com/CloudWise/fly-fish.git",
        trino_config,
        "2022-02-24",
        analysis_id,
    )


def export_test_data_set():
    # 获取路径下的json文件
    config_files = []
    for filename in os.listdir(save_data_path):
        if os.path.isfile(os.path.join(save_data_path, filename)) and filename.endswith(
            ".json"
        ):
            config_files.append(os.path.join(save_data_path, filename))

    # 请使用者输入想生成哪个文件
    for index, config_file in enumerate(config_files):
        print("[{}] {}".format(index, config_file))
    configIndex = int(input("input which .json would you like: "))
    config_file = config_files[configIndex]

    # 读取配置文件
    with open(config_file, "r") as config_f:
        config: ConfigDefine = json.load(config_f)
        # project_id
        if config_file.endswith("pg-ee-project.json"):
            check_pg_data(config)
            export_pg_data(
                "https://gitee.com/CloudWise/fly-fish.git",
                config,
                "2583d35b-838f-4852-b08d-79732c28b72a",
            )
        elif config_file.endswith("pg-ee-report2.json"):
            check_pg_data(config)
            # report_id
            export_pg_data(
                "https://gitee.com/CloudWise/fly-fish.git",
                config,
                "b3727e99-555d-4f35-815f-b96886d071aa",
            )
            # import_pg_data('http://gitlab.com:merico-dev/ee/vdev.co.git', config, 'eef8c6d1-ce99-401a-8bc8-721a05357f41')
        elif config["type"] == "trino":
            # 这里的id是analysisId 通过Select * from project_report_state where report_id='dadb9476-cdd4-440a-8579-853a8d18bc32' 来查询
            export_trino_data(
                "https://gitee.com/CloudWise/fly-fish.git",
                config,
                "2022-02-24",
                "b3801188-f2c8-4e7f-b2c4-40995e16d313",
            )


def update_change_line(raw):
    return raw.replace("\\n", "\n")


def remove_team_user(email):
    sql = f"SELECT team_user.id FROM team_user join users ON team_user.user_id=users.id WHERE users.primary_email='{email}'"
    team_user_id = query_one_from_db(sql, "id")
    if team_user_id is not None:
        base_url = os.getenv("EE_BASE_URL")
        token = get_token()
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
        }
        response = requests.post(
            f"{base_url}/teamUser/batchDeleteTeamUser",
            json={"params": [[team_user_id]]},
            headers=headers,
        )
        assert response.status_code == 200


if __name__ == "__main__":
    # export_test_data_set()
    remove_team_user("june.yang@yunzhihui.com")
