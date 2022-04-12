from httprunner import HttpRunner, Config, Step, RunRequest


class TestCaseCan(HttpRunner):
    config = Config("user login").variables().base_url("${ENV(EE_BASE_URL)}")

    teststeps = [
        Step(
            RunRequest("判断用户是否有权限")
            .setup_hook("${before_request($request)}")
            .post("/user/can")
            .with_json({"params": []})
            .validate()
            .assert_equal("status_code", 200)
            .assert_type_match("body", bool)
        ),
        Step(
            RunRequest("用户未认证")
            .post("/user/can")
            .with_json({"params": []})
            .validate()
            .assert_equal("status_code", 401)
            .assert_equal("body.code", "NOT_AUTHENTICATED")
        ),
    ]


if __name__ == "__main__":
    TestCaseCan().test_start()
