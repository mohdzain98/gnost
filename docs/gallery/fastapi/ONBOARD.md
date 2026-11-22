# fastapi — Project Onboarding Guide

_Generated automatically by <a href='https://gnost.readthedocs.io'>GNOST</a>._

## Project Overview

- **Root:** `https://github.com/fastapi/fastapi`
- **Languages:** python (557), javascript (4)
- **Framework:** Flask

## Summary Table

| Language | Files | LOC |
|---|---:|---:|
| JavaScript | 4 | 614 |
| Python | 1233 | 136181 |

## Stats Table

| Language | Files | Code | Comments | Blanks | LOC |
|---|---:|---:|---:|---:|---:|
| JavaScript | 4 | 557 | 9 | 48 | 614 |
| Python | 1233 | 116202 | 903 | 19076 | 136181 |

## Get it running

_Read from this project's own files. Each line names its source; nothing is guessed._

**Prerequisites**

- Python >=3.11 _(pyproject.toml)_

**Install**

- `uv sync` _(pyproject.toml)_

**Run**

- `fastapi` _(pyproject.toml)_

**Test**

- `pytest` _(pyproject.toml)_

## Entry Points

- `docs_src/additional_responses/tutorial001.py` — FastAPI app initialization
- `docs_src/additional_responses/tutorial002.py` — FastAPI app initialization
- `docs_src/additional_responses/tutorial003.py` — FastAPI app initialization
- `docs_src/additional_responses/tutorial004.py` — FastAPI app initialization
- `docs_src/additional_status_codes/tutorial001.py` — FastAPI app initialization
- `docs_src/additional_status_codes/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/advanced_middleware/tutorial001.py` — FastAPI app initialization
- `docs_src/advanced_middleware/tutorial002.py` — FastAPI app initialization
- `docs_src/advanced_middleware/tutorial003.py` — FastAPI app initialization
- `docs_src/app_testing/app_a/main.py` — FastAPI app initialization
- `docs_src/app_testing/app_b/main.py` — FastAPI app initialization
- `docs_src/app_testing/app_b_non_an/main.py` — FastAPI app initialization
- `docs_src/app_testing/tutorial001.py` — FastAPI app initialization
- `docs_src/app_testing/tutorial002.py` — FastAPI app initialization
- `docs_src/app_testing/tutorial003.py` — FastAPI app initialization
- `docs_src/app_testing/tutorial004.py` — FastAPI app initialization
- `docs_src/async_tests/app_a/main.py` — FastAPI app initialization
- `docs_src/authentication_error_status_code/tutorial001.py` — FastAPI app initialization
- `docs_src/background_tasks/tutorial001.py` — FastAPI app initialization
- `docs_src/background_tasks/tutorial002.py` — FastAPI app initialization
- `docs_src/background_tasks/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/behind_a_proxy/tutorial001.py` — FastAPI app initialization
- `docs_src/behind_a_proxy/tutorial001_01.py` — FastAPI app initialization
- `docs_src/behind_a_proxy/tutorial002.py` — FastAPI app initialization
- `docs_src/behind_a_proxy/tutorial003.py` — FastAPI app initialization
- `docs_src/behind_a_proxy/tutorial004.py` — FastAPI app initialization
- `docs_src/bigger_applications/app/main.py` — FastAPI app initialization
- `docs_src/body/tutorial001.py` — FastAPI app initialization
- `docs_src/body/tutorial002.py` — FastAPI app initialization
- `docs_src/body/tutorial003.py` — FastAPI app initialization
- `docs_src/body/tutorial004.py` — FastAPI app initialization
- `docs_src/body_fields/tutorial001.py` — FastAPI app initialization
- `docs_src/body_fields/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial001.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial002.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial003.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial004.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial005.py` — FastAPI app initialization
- `docs_src/body_multiple_params/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial001.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial002.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial003.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial004.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial005.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial006.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial007.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial008.py` — FastAPI app initialization
- `docs_src/body_nested_models/tutorial009.py` — FastAPI app initialization
- `docs_src/body_updates/tutorial001.py` — FastAPI app initialization
- `docs_src/body_updates/tutorial002.py` — FastAPI app initialization
- `docs_src/conditional_openapi/tutorial001.py` — FastAPI app initialization
- `docs_src/configure_swagger_ui/tutorial001.py` — FastAPI app initialization
- `docs_src/configure_swagger_ui/tutorial002.py` — FastAPI app initialization
- `docs_src/configure_swagger_ui/tutorial003.py` — FastAPI app initialization
- `docs_src/cookie_param_models/tutorial001.py` — FastAPI app initialization
- `docs_src/cookie_param_models/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/cookie_param_models/tutorial002.py` — FastAPI app initialization
- `docs_src/cookie_param_models/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/cookie_param_models/tutorial003.py` — FastAPI app initialization
- `docs_src/cookie_param_models/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/cookie_params/tutorial001.py` — FastAPI app initialization
- `docs_src/cookie_params/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/cors/tutorial001.py` — FastAPI app initialization
- `docs_src/custom_docs_ui/tutorial001.py` — FastAPI app initialization
- `docs_src/custom_docs_ui/tutorial002.py` — FastAPI app initialization
- `docs_src/custom_request_and_route/tutorial001.py` — FastAPI app initialization
- `docs_src/custom_request_and_route/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/custom_request_and_route/tutorial002.py` — FastAPI app initialization
- `docs_src/custom_request_and_route/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/custom_request_and_route/tutorial003.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial001.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial001b.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial002.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial003.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial004.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial005.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial006.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial006b.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial006c.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial007.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial008.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial009.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial009b.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial009c.py` — FastAPI app initialization
- `docs_src/custom_response/tutorial010.py` — FastAPI app initialization
- `docs_src/dataclasses_/tutorial001.py` — FastAPI app initialization
- `docs_src/dataclasses_/tutorial002.py` — FastAPI app initialization
- `docs_src/dataclasses_/tutorial003.py` — FastAPI app initialization
- `docs_src/debugging/tutorial001.py` — FastAPI app initialization
- `docs_src/debugging/tutorial001.py` — uvicorn.run
- `docs_src/dependencies/tutorial001.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial001_02.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial002.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial003.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial004.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial005.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial006.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial006_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008b.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008b_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008c.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008c_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008d.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008d_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008e.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial008e_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial011.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial011_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial012.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial012_non_an.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial013.py` — FastAPI app initialization
- `docs_src/dependencies/tutorial014.py` — FastAPI app initialization
- `docs_src/dependency_testing/tutorial001.py` — FastAPI app initialization
- `docs_src/dependency_testing/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/encoder/tutorial001.py` — FastAPI app initialization
- `docs_src/events/tutorial001.py` — FastAPI app initialization
- `docs_src/events/tutorial002.py` — FastAPI app initialization
- `docs_src/events/tutorial003.py` — FastAPI app initialization
- `docs_src/extending_openapi/tutorial001.py` — FastAPI app initialization
- `docs_src/extra_data_types/tutorial001.py` — FastAPI app initialization
- `docs_src/extra_data_types/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/extra_models/tutorial001.py` — FastAPI app initialization
- `docs_src/extra_models/tutorial002.py` — FastAPI app initialization
- `docs_src/extra_models/tutorial003.py` — FastAPI app initialization
- `docs_src/extra_models/tutorial004.py` — FastAPI app initialization
- `docs_src/extra_models/tutorial005.py` — FastAPI app initialization
- `docs_src/first_steps/tutorial001.py` — FastAPI app initialization
- `docs_src/first_steps/tutorial003.py` — FastAPI app initialization
- `docs_src/frontend/tutorial001.py` — FastAPI app initialization
- `docs_src/frontend/tutorial002.py` — FastAPI app initialization
- `docs_src/frontend/tutorial003.py` — FastAPI app initialization
- `docs_src/frontend/tutorial004.py` — FastAPI app initialization
- `docs_src/frontend/tutorial005.py` — FastAPI app initialization
- `docs_src/frontend/tutorial006.py` — FastAPI app initialization
- `docs_src/generate_clients/tutorial001.py` — FastAPI app initialization
- `docs_src/generate_clients/tutorial002.py` — FastAPI app initialization
- `docs_src/generate_clients/tutorial003.py` — FastAPI app initialization
- `docs_src/graphql_/tutorial001.py` — FastAPI app initialization
- `docs_src/handling_errors/tutorial001.py` — FastAPI app initialization
- `docs_src/handling_errors/tutorial002.py` — FastAPI app initialization
- `docs_src/handling_errors/tutorial003.py` — FastAPI app initialization
- `docs_src/handling_errors/tutorial004.py` — FastAPI app initialization
- `docs_src/handling_errors/tutorial005.py` — FastAPI app initialization
- `docs_src/handling_errors/tutorial006.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial001.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial002.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial003.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial004.py` — FastAPI app initialization
- `docs_src/header_param_models/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/header_params/tutorial001.py` — FastAPI app initialization
- `docs_src/header_params/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/header_params/tutorial002.py` — FastAPI app initialization
- `docs_src/header_params/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/header_params/tutorial003.py` — FastAPI app initialization
- `docs_src/header_params/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/json_base64_bytes/tutorial001.py` — FastAPI app initialization
- `docs_src/metadata/tutorial001.py` — FastAPI app initialization
- `docs_src/metadata/tutorial001_1.py` — FastAPI app initialization
- `docs_src/metadata/tutorial002.py` — FastAPI app initialization
- `docs_src/metadata/tutorial003.py` — FastAPI app initialization
- `docs_src/metadata/tutorial004.py` — FastAPI app initialization
- `docs_src/middleware/tutorial001.py` — FastAPI app initialization
- `docs_src/openapi_callbacks/tutorial001.py` — FastAPI app initialization
- `docs_src/openapi_webhooks/tutorial001.py` — FastAPI app initialization
- `docs_src/opentelemetry/tutorial001.py` — FastAPI app initialization
- `docs_src/opentelemetry/tutorial002.py` — FastAPI app initialization
- `docs_src/opentelemetry/tutorial003.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial001.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial002.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial003.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial004.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial005.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial006.py` — FastAPI app initialization
- `docs_src/path_operation_advanced_configuration/tutorial007.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial001.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial002.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial002b.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial003.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial004.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial005.py` — FastAPI app initialization
- `docs_src/path_operation_configuration/tutorial006.py` — FastAPI app initialization
- `docs_src/path_params/tutorial001.py` — FastAPI app initialization
- `docs_src/path_params/tutorial002.py` — FastAPI app initialization
- `docs_src/path_params/tutorial003.py` — FastAPI app initialization
- `docs_src/path_params/tutorial003b.py` — FastAPI app initialization
- `docs_src/path_params/tutorial004.py` — FastAPI app initialization
- `docs_src/path_params/tutorial005.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial001.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial002.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial003.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial004.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial005.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial006.py` — FastAPI app initialization
- `docs_src/path_params_numeric_validations/tutorial006_non_an.py` — FastAPI app initialization
- `docs_src/pydantic_v1_in_v2/tutorial002.py` — FastAPI app initialization
- `docs_src/pydantic_v1_in_v2/tutorial003.py` — FastAPI app initialization
- `docs_src/pydantic_v1_in_v2/tutorial004.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial001.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial002.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial003.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial004.py` — FastAPI app initialization
- `docs_src/query_param_models/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/query_params/tutorial001.py` — FastAPI app initialization
- `docs_src/query_params/tutorial002.py` — FastAPI app initialization
- `docs_src/query_params/tutorial003.py` — FastAPI app initialization
- `docs_src/query_params/tutorial004.py` — FastAPI app initialization
- `docs_src/query_params/tutorial005.py` — FastAPI app initialization
- `docs_src/query_params/tutorial006.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial001.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial002.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial003.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial004.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial005.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial006.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial006_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial006c.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial006c_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial007.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial007_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial008.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial008_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial009.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial009_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial010.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial010_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial011.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial011_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial012.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial012_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial013.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial013_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial014.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial014_non_an.py` — FastAPI app initialization
- `docs_src/query_params_str_validations/tutorial015.py` — FastAPI app initialization
- `docs_src/request_body_limits/tutorial001.py` — FastAPI app initialization
- `docs_src/request_body_limits/tutorial002.py` — FastAPI app initialization
- `docs_src/request_files/tutorial001.py` — FastAPI app initialization
- `docs_src/request_files/tutorial001_02.py` — FastAPI app initialization
- `docs_src/request_files/tutorial001_02_non_an.py` — FastAPI app initialization
- `docs_src/request_files/tutorial001_03.py` — FastAPI app initialization
- `docs_src/request_files/tutorial001_03_non_an.py` — FastAPI app initialization
- `docs_src/request_files/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/request_files/tutorial002.py` — FastAPI app initialization
- `docs_src/request_files/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/request_files/tutorial003.py` — FastAPI app initialization
- `docs_src/request_files/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial001.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial002.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial003.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial004.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial005.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial006.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial006_non_an.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial007.py` — FastAPI app initialization
- `docs_src/request_form_models/tutorial007_non_an.py` — FastAPI app initialization
- `docs_src/request_forms/tutorial001.py` — FastAPI app initialization
- `docs_src/request_forms/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/request_forms/tutorial002.py` — FastAPI app initialization
- `docs_src/request_forms/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/request_forms_and_files/tutorial001.py` — FastAPI app initialization
- `docs_src/request_forms_and_files/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/response_change_status_code/tutorial001.py` — FastAPI app initialization
- `docs_src/response_cookies/tutorial001.py` — FastAPI app initialization
- `docs_src/response_cookies/tutorial002.py` — FastAPI app initialization
- `docs_src/response_directly/tutorial001.py` — FastAPI app initialization
- `docs_src/response_directly/tutorial002.py` — FastAPI app initialization
- `docs_src/response_headers/tutorial001.py` — FastAPI app initialization
- `docs_src/response_headers/tutorial002.py` — FastAPI app initialization
- `docs_src/response_model/tutorial001.py` — FastAPI app initialization
- `docs_src/response_model/tutorial001_01.py` — FastAPI app initialization
- `docs_src/response_model/tutorial002.py` — FastAPI app initialization
- `docs_src/response_model/tutorial003.py` — FastAPI app initialization
- `docs_src/response_model/tutorial003_01.py` — FastAPI app initialization
- `docs_src/response_model/tutorial003_02.py` — FastAPI app initialization
- `docs_src/response_model/tutorial003_03.py` — FastAPI app initialization
- `docs_src/response_model/tutorial003_04.py` — FastAPI app initialization
- `docs_src/response_model/tutorial003_05.py` — FastAPI app initialization
- `docs_src/response_model/tutorial004.py` — FastAPI app initialization
- `docs_src/response_model/tutorial005.py` — FastAPI app initialization
- `docs_src/response_model/tutorial006.py` — FastAPI app initialization
- `docs_src/response_status_code/tutorial001.py` — FastAPI app initialization
- `docs_src/response_status_code/tutorial002.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial001.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial002.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial003.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial004.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial005.py` — FastAPI app initialization
- `docs_src/schema_extra_example/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial001.py` — FastAPI app initialization
- `docs_src/security/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial002.py` — FastAPI app initialization
- `docs_src/security/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial003.py` — FastAPI app initialization
- `docs_src/security/tutorial003_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial004.py` — FastAPI app initialization
- `docs_src/security/tutorial004_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial005.py` — FastAPI app initialization
- `docs_src/security/tutorial005_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial006.py` — FastAPI app initialization
- `docs_src/security/tutorial006_non_an.py` — FastAPI app initialization
- `docs_src/security/tutorial007.py` — FastAPI app initialization
- `docs_src/security/tutorial007_non_an.py` — FastAPI app initialization
- `docs_src/separate_openapi_schemas/tutorial001.py` — FastAPI app initialization
- `docs_src/separate_openapi_schemas/tutorial002.py` — FastAPI app initialization
- `docs_src/server_sent_events/tutorial001.py` — FastAPI app initialization
- `docs_src/server_sent_events/tutorial002.py` — FastAPI app initialization
- `docs_src/server_sent_events/tutorial003.py` — FastAPI app initialization
- `docs_src/server_sent_events/tutorial004.py` — FastAPI app initialization
- `docs_src/server_sent_events/tutorial005.py` — FastAPI app initialization
- `docs_src/settings/app01/main.py` — FastAPI app initialization
- `docs_src/settings/app02/main.py` — FastAPI app initialization
- `docs_src/settings/app02_non_an/main.py` — FastAPI app initialization
- `docs_src/settings/app03/main.py` — FastAPI app initialization
- `docs_src/settings/app03_non_an/main.py` — FastAPI app initialization
- `docs_src/settings/tutorial001.py` — FastAPI app initialization
- `docs_src/sql_databases/tutorial001.py` — FastAPI app initialization
- `docs_src/sql_databases/tutorial001_non_an.py` — FastAPI app initialization
- `docs_src/sql_databases/tutorial002.py` — FastAPI app initialization
- `docs_src/sql_databases/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/static_files/tutorial001.py` — FastAPI app initialization
- `docs_src/stream_data/tutorial001.py` — FastAPI app initialization
- `docs_src/stream_data/tutorial002.py` — FastAPI app initialization
- `docs_src/stream_json_lines/tutorial001.py` — FastAPI app initialization
- `docs_src/strict_content_type/tutorial001.py` — FastAPI app initialization
- `docs_src/sub_applications/tutorial001.py` — FastAPI app initialization
- `docs_src/templates/tutorial001.py` — FastAPI app initialization
- `docs_src/templates/tutorial002.py` — FastAPI app initialization
- `docs_src/using_request_directly/tutorial001.py` — FastAPI app initialization
- `docs_src/websockets_/tutorial001.py` — FastAPI app initialization
- `docs_src/websockets_/tutorial002.py` — FastAPI app initialization
- `docs_src/websockets_/tutorial002_non_an.py` — FastAPI app initialization
- `docs_src/websockets_/tutorial003.py` — FastAPI app initialization
- `docs_src/wsgi/tutorial001.py` — FastAPI app initialization
- `docs_src/wsgi/tutorial001.py` — Flask app initialization
- `docs_src/debugging/tutorial001.py` — __main__ guard
- `scripts/add_latest_release_date.py` — __main__ guard
- `scripts/deploy_docs_status.py` — __main__ guard
- `scripts/docs.py` — __main__ guard
- `scripts/prepare_release.py` — __main__ guard
- `scripts/sponsors.py` — __main__ guard
- `scripts/topic_repos.py` — __main__ guard
- `scripts/translate.py` — __main__ guard
- `scripts/translation_fixer.py` — __main__ guard

## Routes

468 endpoints found. Each row is a URL and the code that handles it.

| Method | Path | Handler | File |
|---|---|---|---|
| GET | `/` | `main` | `docs_src/advanced_middleware/tutorial001.py:10` |
| GET | `/` | `main` | `docs_src/advanced_middleware/tutorial002.py:12` |
| GET | `/` | `main` | `docs_src/advanced_middleware/tutorial003.py:10` |
| GET | `/` | `read_main` | `docs_src/app_testing/app_a/main.py:7` |
| GET | `/` | `read_main` | `docs_src/app_testing/tutorial001.py:8` |
| GET | `/` | `read_main` | `docs_src/app_testing/tutorial002.py:9` |
| GET | `/` | `root` | `docs_src/async_tests/app_a/main.py:7` |
| GET | `/` | `root` | `docs_src/bigger_applications/app/main.py:22` |
| GET | `/` | `root` | `docs_src/conditional_openapi/tutorial001.py:15` |
| GET | `/` | `main` | `docs_src/cors/tutorial001.py:23` |
| GET | `/` | `not_timed` | `docs_src/custom_request_and_route/tutorial003.py:30` |
| GET | `/` | `main` | `docs_src/custom_response/tutorial005.py:8` |
| GET | `/` | `main` | `docs_src/custom_response/tutorial007.py:15` |
| GET | `/` | `main` | `docs_src/custom_response/tutorial008.py:9` |
| GET | `/` | `main` | `docs_src/custom_response/tutorial009.py:9` |
| GET | `/` | `main` | `docs_src/custom_response/tutorial009b.py:9` |
| GET | `/` | `main` | `docs_src/custom_response/tutorial009c.py:18` |
| GET | `/` | `root` | `docs_src/debugging/tutorial001.py:8` |
| GET | `/` | `root` | `docs_src/first_steps/tutorial001.py:7` |
| GET | `/` | `root` | `docs_src/first_steps/tutorial003.py:7` |
| GET | `/` | `main` | `docs_src/request_files/tutorial002.py:20` |
| GET | `/` | `main` | `docs_src/request_files/tutorial002_non_an.py:18` |
| GET | `/` | `main` | `docs_src/request_files/tutorial003.py:26` |
| GET | `/` | `main` | `docs_src/request_files/tutorial003_non_an.py:22` |
| GET | `/` | `get` | `docs_src/websockets_/tutorial001.py:42` |
| GET | `/` | `get` | `docs_src/websockets_/tutorial002.py:62` |
| GET | `/` | `get` | `docs_src/websockets_/tutorial002_non_an.py:60` |
| GET | `/` | `get` | `docs_src/websockets_/tutorial003.py:67` |
| GET | `/` | `flask_main` | `docs_src/wsgi/tutorial001.py:10` |
| POST | `/` | `sum_numbers` | `docs_src/custom_request_and_route/tutorial002.py:29` |
| POST | `/` | `sum_numbers` | `docs_src/custom_request_and_route/tutorial002_non_an.py:28` |
| GET | `/<dynamic>` | `swagger_ui_redirect` | `docs_src/custom_docs_ui/tutorial001.py:23` |
| GET | `/<dynamic>` | `swagger_ui_redirect` | `docs_src/custom_docs_ui/tutorial002.py:26` |
| POST | `/admin` | `update_admin` | `docs_src/bigger_applications/app/internal/admin.py:7` |
| GET | `/app` | `read_main` | `docs_src/behind_a_proxy/tutorial001.py:7` |
| GET | `/app` | `read_main` | `docs_src/behind_a_proxy/tutorial002.py:7` |
| GET | `/app` | `read_main` | `docs_src/behind_a_proxy/tutorial003.py:12` |
| GET | `/app` | `read_main` | `docs_src/behind_a_proxy/tutorial004.py:13` |
| GET | `/app` | `read_main` | `docs_src/sub_applications/tutorial001.py:7` |
| GET | `/authors/` | `get_authors` | `docs_src/dataclasses_/tutorial003.py:28` |

_...and 428 more; the full list is in the insights JSON (`--json`)._

## Execution Flow (High Level)

- `docs_src/additional_responses/tutorial001.py` → `fastapi/__init__.py` → `fastapi/exceptions.py`
- `docs_src/additional_responses/tutorial001.py` → `fastapi/__init__.py` → `fastapi/requests.py`
- `docs_src/additional_responses/tutorial001.py` → `fastapi/__init__.py` → `fastapi/websockets.py`
- `docs_src/additional_responses/tutorial001.py` → `fastapi/responses.py` → `fastapi/sse.py`
- `docs_src/additional_responses/tutorial001.py` → `fastapi/__init__.py` → `fastapi/applications.py` → `fastapi/_body_limit.py`

_(8440 additional paths omitted for clarity.)_

## Function-level Flow

What each entry point calls, function by function (Python only; calls through other objects such as `self.client.send()` are not followed). Full diagrams: [function-flow.md](flow/function-flow.md).

### `POST /token` → `login_for_access_token`

`docs_src/security/tutorial004.py:122`

- `authenticate_user` (`docs_src/security/tutorial004.py:72`)
  - `get_user` (`docs_src/security/tutorial004.py:66`)
  - `verify_password` (`docs_src/security/tutorial004.py:58`)
- `create_access_token` (`docs_src/security/tutorial004.py:82`)

### `GET /docs` → `custom_swagger_ui_html`

`docs_src/custom_docs_ui/tutorial001.py:12`

- `get_swagger_ui_html` (`fastapi/openapi/docs.py:40`)
  - `_html_safe_json` (`fastapi/openapi/docs.py:9`)
  - `jsonable_encoder` (`fastapi/encoders.py:129`)

### `POST /user/` → `create_user`

`docs_src/extra_models/tutorial001.py:39`

- `fake_save_user` (`docs_src/extra_models/tutorial001.py:31`)
  - `fake_password_hasher` (`docs_src/extra_models/tutorial001.py:27`)

### `GET /` → `main`

`docs_src/custom_response/tutorial007.py:15`

- `fake_video_streamer` (`docs_src/custom_response/tutorial007.py:8`)

### `GET /<dynamic>` → `swagger_ui_redirect`

`docs_src/custom_docs_ui/tutorial001.py:23`

- `get_swagger_ui_oauth2_redirect_html` (`fastapi/openapi/docs.py:301`)

_...and 14 more entry points in the insights JSON (`--json`)._

## Execution Flow (Overview)

```mermaid
flowchart TD
  dir_docs_src_security["docs_src/security<br/>14 files"]
  dir_fastapi["fastapi<br/>12 files"]
  dir_docs_src_response_model["docs_src/response_model<br/>12 files"]
  dir_docs_src_cookie_param_models["docs_src/cookie_param_models<br/>6 files"]
  dir_docs_src_dependencies["docs_src/dependencies<br/>27 files"]
  dir_docs_src_custom_request_and_route["docs_src/custom_request_and_route<br/>5 files"]
  dir_docs_src_body_nested_models["docs_src/body_nested_models<br/>9 files"]
  dir_fastapi_openapi["fastapi/openapi<br/>3 files"]
  dir_fastapi_dependencies["fastapi/dependencies<br/>2 files"]
  dir_docs_src_request_form_models["docs_src/request_form_models<br/>14 files"]
  dir_docs_src_request_files["docs_src/request_files<br/>10 files"]
  dir_docs_src_conditional_openapi["docs_src/conditional_openapi<br/>1 file"]
  dir_docs_src_response_cookies["docs_src/response_cookies<br/>2 files"]
  dir_docs_src_response_directly["docs_src/response_directly<br/>2 files"]
  dir_docs_src_websockets_["docs_src/websockets_<br/>4 files"]
  dir_docs_src_stream_data["docs_src/stream_data<br/>2 files"]
  dir_docs_src_body_fields["docs_src/body_fields<br/>2 files"]
  dir_fastapi_security["fastapi/security<br/>6 files"]
  dir_docs_src_server_sent_events["docs_src/server_sent_events<br/>5 files"]
  dir_docs_src_query_params_str_validations["docs_src/query_params_str_validations<br/>30 files"]
  dir_docs_src_path_operation_configuration["docs_src/path_operation_configuration<br/>7 files"]
  dir_fastapi__compat["fastapi/_compat<br/>3 files"]
  dir_docs_src_handling_errors["docs_src/handling_errors<br/>6 files"]
  dir_docs_src_static_files["docs_src/static_files<br/>1 file"]
  dir_docs_src_extra_models["docs_src/extra_models<br/>5 files"]
  dir_docs_src_header_param_models["docs_src/header_param_models<br/>8 files"]
  dir_docs_src_dataclasses_["docs_src/dataclasses_<br/>3 files"]
  dir_docs_src_strict_content_type["docs_src/strict_content_type<br/>1 file"]
  dir_docs_src_schema_extra_example["docs_src/schema_extra_example<br/>8 files"]
  dir_docs_src_query_params["docs_src/query_params<br/>6 files"]
  dir_docs_src_settings_app03_non_an["docs_src/settings/app03_non_an<br/>1 file"]
  dir_docs_src_custom_response["docs_src/custom_response<br/>15 files"]
  dir_docs_src_header_params["docs_src/header_params<br/>6 files"]
  dir_docs_src_additional_responses["docs_src/additional_responses<br/>4 files"]
  dir_docs_src_separate_openapi_schemas["docs_src/separate_openapi_schemas<br/>2 files"]
  dir_docs_src_pydantic_v1_in_v2["docs_src/pydantic_v1_in_v2<br/>3 files"]
  dir_docs_src_response_headers["docs_src/response_headers<br/>2 files"]
  dir_docs_src_background_tasks["docs_src/background_tasks<br/>3 files"]
  dir_docs_src_path_params["docs_src/path_params<br/>6 files"]
  dir_docs_src_body_multiple_params["docs_src/body_multiple_params<br/>9 files"]
  dir_docs_src_request_forms["docs_src/request_forms<br/>4 files"]
  dir_docs_src_settings_app03["docs_src/settings/app03<br/>1 file"]
  dir_docs_src_graphql_["docs_src/graphql_<br/>1 file"]
  dir_docs_src_openapi_webhooks["docs_src/openapi_webhooks<br/>1 file"]
  dir_docs_src_generate_clients["docs_src/generate_clients<br/>3 files"]
  dir_docs_src_additional_status_codes["docs_src/additional_status_codes<br/>2 files"]
  dir_docs_src_behind_a_proxy["docs_src/behind_a_proxy<br/>5 files"]
  dir_docs_src_frontend["docs_src/frontend<br/>6 files"]
  dir_docs_src_configure_swagger_ui["docs_src/configure_swagger_ui<br/>3 files"]
  dir_docs_src_sql_databases["docs_src/sql_databases<br/>4 files"]
  dir_docs_src_app_testing["docs_src/app_testing<br/>4 files"]
  dir_docs_src_response_status_code["docs_src/response_status_code<br/>2 files"]
  dir_docs_src_path_params_numeric_validations["docs_src/path_params_numeric_validations<br/>12 files"]
  dir_docs_src_bigger_applications_app_internal["docs_src/bigger_applications/app/internal<br/>1 file"]
  dir_docs_src_path_operation_advanced_configuration["docs_src/path_operation_advanced_configuration<br/>7 files"]
  dir_docs_src_templates["docs_src/templates<br/>2 files"]
  dir_docs_src_authentication_error_status_code["docs_src/authentication_error_status_code<br/>1 file"]
  dir_docs_src_app_testing_app_b_non_an["docs_src/app_testing/app_b_non_an<br/>1 file"]
  dir_docs_src_custom_docs_ui["docs_src/custom_docs_ui<br/>2 files"]
  dir_fastapi_telemetry["fastapi/telemetry<br/>4 files"]
  dir_docs_src_dependency_testing["docs_src/dependency_testing<br/>2 files"]
  dir_docs_src_settings_app01["docs_src/settings/app01<br/>1 file"]
  dir_docs_src_metadata["docs_src/metadata<br/>5 files"]
  dir_docs_src_body_updates["docs_src/body_updates<br/>2 files"]
  dir_docs_src_settings["docs_src/settings<br/>1 file"]
  dir_docs_src_cookie_params["docs_src/cookie_params<br/>2 files"]
  dir_docs_src_advanced_middleware["docs_src/advanced_middleware<br/>3 files"]
  dir_docs_src_query_param_models["docs_src/query_param_models<br/>8 files"]
  dir_docs_src_extending_openapi["docs_src/extending_openapi<br/>1 file"]
  dir_docs_src_bigger_applications_app_routers["docs_src/bigger_applications/app/routers<br/>2 files"]
  dir_docs_src_request_body_limits["docs_src/request_body_limits<br/>2 files"]
  dir_docs_src_opentelemetry["docs_src/opentelemetry<br/>3 files"]
  dir_docs_src_bigger_applications_app["docs_src/bigger_applications/app<br/>2 files"]
  dir_docs_src_cors["docs_src/cors<br/>1 file"]
  dir_docs_src_middleware["docs_src/middleware<br/>1 file"]
  dir_docs_src_app_testing_app_b["docs_src/app_testing/app_b<br/>1 file"]
  dir_docs_src_debugging["docs_src/debugging<br/>1 file"]
  dir_docs_src_extra_data_types["docs_src/extra_data_types<br/>2 files"]
  dir_docs_src_body["docs_src/body<br/>4 files"]
  dir_docs_src_request_forms_and_files["docs_src/request_forms_and_files<br/>2 files"]
  dir_docs_src_events["docs_src/events<br/>3 files"]
  dir_docs_src_encoder["docs_src/encoder<br/>1 file"]
  dir_docs_src_first_steps["docs_src/first_steps<br/>2 files"]
  dir_docs_src_stream_json_lines["docs_src/stream_json_lines<br/>1 file"]
  dir_docs_src_wsgi["docs_src/wsgi<br/>1 file"]
  dir_docs_src_response_change_status_code["docs_src/response_change_status_code<br/>1 file"]
  dir_docs_src_app_testing_app_a["docs_src/app_testing/app_a<br/>1 file"]
  dir_docs_src_settings_app02["docs_src/settings/app02<br/>1 file"]
  dir_docs_src_using_request_directly["docs_src/using_request_directly<br/>1 file"]
  dir_docs_src_openapi_callbacks["docs_src/openapi_callbacks<br/>1 file"]
  dir_docs_src_async_tests_app_a["docs_src/async_tests/app_a<br/>1 file"]
  dir_docs_src_json_base64_bytes["docs_src/json_base64_bytes<br/>1 file"]
  dir_docs_src_sub_applications["docs_src/sub_applications<br/>1 file"]
  dir_docs_src_settings_app02_non_an["docs_src/settings/app02_non_an<br/>1 file"]
  dir_docs_src_authentication_error_status_code --> dir_fastapi_security
  dir_docs_src_bigger_applications_app --> dir_docs_src_bigger_applications_app_internal
  dir_docs_src_bigger_applications_app -->|2| dir_docs_src_bigger_applications_app_routers
  dir_docs_src_bigger_applications_app_routers --> dir_docs_src_bigger_applications_app
  dir_docs_src_custom_docs_ui -->|2| dir_fastapi_openapi
  dir_docs_src_extending_openapi --> dir_fastapi_openapi
  dir_docs_src_security -->|14| dir_fastapi_security
  dir_fastapi -.->|7| dir_fastapi__compat
  dir_fastapi ==>|2| dir_fastapi_dependencies
  dir_fastapi ==>|4| dir_fastapi_openapi
  dir_fastapi ==>|5| dir_fastapi_telemetry
  dir_fastapi__compat -.->|2| dir_fastapi
  dir_fastapi_dependencies ==>|4| dir_fastapi
  dir_fastapi_dependencies -->|2| dir_fastapi__compat
  dir_fastapi_dependencies ==>|2| dir_fastapi_security
  dir_fastapi_openapi ==>|8| dir_fastapi
  dir_fastapi_openapi -->|2| dir_fastapi__compat
  dir_fastapi_openapi ==>|2| dir_fastapi_dependencies
  dir_fastapi_security ==> dir_fastapi
  dir_fastapi_security -->|5| dir_fastapi_openapi
  dir_fastapi_telemetry ==> dir_fastapi
  linkStyle 7,11 stroke:#f57c00,stroke-width:2px
  linkStyle 8,9,10,12,14,15,17,18,20 stroke:#d32f2f,stroke-width:3px
  linkStyle 13,16,19 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class dir_fastapi,dir_fastapi_openapi,dir_fastapi_dependencies,dir_fastapi_security,dir_fastapi_telemetry cycle
```

> Grouped by folder to stay readable: 94 folders; numbers on arrows count the file-level imports they stand for.
> Arrows into `fastapi` are not drawn: most folders import them, and drawing every arrow would hide the structure.
> Thick red arrows: circular imports that happen as modules load.
> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

> 📌 This diagram shows the high-level execution flow.<br>For the complete flow, see [**flow/flow-full.md**](./flow/FLOW-full.md)<br>Raw Mermaid: [flow/flow-full.mmd](./flow/FLOW-full.mmd)<br>Every file and import, ungrouped (for tools and AI): [flow/flow-complete.mmd](./flow/flow-complete.mmd)<br>Interactive explorer: run `gnost open flow` (the page is `flow.html` in this folder; it is rebuilt, not committed)

## Recommended Reading Order

### Start Here

- `docs_src/additional_responses/tutorial001.py`
- `docs_src/additional_responses/tutorial002.py`
- `docs_src/additional_responses/tutorial003.py`
- `docs_src/additional_responses/tutorial004.py`
- `docs_src/additional_status_codes/tutorial001.py`
- `docs_src/additional_status_codes/tutorial001_non_an.py`
- `docs_src/advanced_middleware/tutorial001.py`
- `docs_src/advanced_middleware/tutorial002.py`
- `docs_src/advanced_middleware/tutorial003.py`
- `docs_src/app_testing/app_a/main.py`
- `docs_src/app_testing/app_b/main.py`
- `docs_src/app_testing/app_b_non_an/main.py`
- `docs_src/app_testing/tutorial001.py`
- `docs_src/app_testing/tutorial002.py`
- `docs_src/app_testing/tutorial003.py`
- _...and 347 more (closest to an entry point listed first)_

### Core Logic

- `docs_src/bigger_applications/app/dependencies.py`
- `docs_src/bigger_applications/app/internal/admin.py`
- `docs_src/bigger_applications/app/routers/items.py`
- `docs_src/bigger_applications/app/routers/users.py`
- `fastapi/__init__.py`
- `fastapi/encoders.py`
- `fastapi/exception_handlers.py`
- `fastapi/openapi/docs.py`
- `fastapi/openapi/utils.py`
- `fastapi/responses.py`
- `fastapi/routing.py`
- `fastapi/security/__init__.py`
- `fastapi/_body_limit.py`
- `fastapi/_compat/__init__.py`
- `fastapi/applications.py`
- _...and 19 more (closest to an entry point listed first)_

### Supporting / Leaf Code

- `docs_src/bigger_applications/app/internal/__init__.py`
- `docs_src/bigger_applications/app/routers/__init__.py`
- `docs_src/settings/app01/config.py`
- `docs_src/settings/app02/config.py`
- `docs_src/settings/app02_non_an/config.py`
- `docs_src/settings/app03/__init__.py`
- `docs_src/settings/app03/config.py`
- `docs_src/settings/app03_non_an/__init__.py`
- `docs_src/settings/app03_non_an/config.py`
- `fastapi/exceptions.py`
- `fastapi/middleware/cors.py`
- `fastapi/middleware/gzip.py`
- `fastapi/middleware/httpsredirect.py`
- `fastapi/middleware/trustedhost.py`
- `fastapi/sse.py`
- _...and 12 more (closest to an entry point listed first)_

## 📘 First Files to Read
- **`fastapi/__init__.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/applications.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/routing.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/param_functions.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/responses.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/exceptions.py`**
  - Frequently involved in execution flow
- **`fastapi/websockets.py`**
  - Frequently involved in execution flow
- **`fastapi/background.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/datastructures.py`**
  - Core logic file referenced by multiple execution paths
- **`fastapi/requests.py`**
  - Frequently involved in execution flow

## ⚠️ Caution Areas
### `fastapi/routing.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 99.6/100
- Part of an import-time circular dependency; a function with complexity 31; 6,215 lines of code
### `fastapi/dependencies/utils.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 99.2/100
- Part of an import-time circular dependency; a function with complexity 54; 1,398 lines of code
### `fastapi/openapi/utils.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 98.5/100
- Part of an import-time circular dependency; a function with complexity 46; 641 lines of code
### `fastapi/__init__.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 98.1/100
- Part of an import-time circular dependency; imported by 376 files; imports 9 project files
### `fastapi/encoders.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 97.9/100
- Part of an import-time circular dependency; a function with complexity 35; imported by 9 files
### `fastapi/applications.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 97.7/100
- Part of an import-time circular dependency; 4,446 lines of code; imports 16 project files
### `fastapi/telemetry/_asgi.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 97.6/100
- Part of an import-time circular dependency; a function with complexity 50; 430 lines of code
### `fastapi/param_functions.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 97/100
- Part of an import-time circular dependency; 2,460 lines of code
### `fastapi/params.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 95.4/100
- Part of an import-time circular dependency; 785 lines of code; imported by 6 files
### `fastapi/_compat/v2.py`
- **Type:** circular_dependency
- **Severity:** 5
- **Caution score:** 93.6/100
- Part of an import-time circular dependency; 457 lines of code; a function with complexity 15

## Change Hotspots

_Not available: git log took longer than 120 seconds_

## 🔁 Circular Dependencies

1 import-time, 0 deferred. Import-time cycles load as the modules start and can fail there; deferred ones go through an import inside a function, a type-only import or a dynamic `import()` and are usually intentional.

### Import-time

- `fastapi/__init__.py` → `fastapi/applications.py` → `fastapi/__init__.py` _(group of 20 files)_
## Key Execution Paths

To understand specific scenarios, see the entry-based execution paths:

- 📍 [Entry-based Paths](flow/entry-paths.md)

- 🧭 [folder-based Paths](flow/folder-paths.md)

(Whole system: [flow/FLOW-full.md](flow/FLOW-full.md). For a small project it is the same as [flow/flow-complete.mmd](flow/flow-complete.mmd), every file and import; for a big one FLOW-full groups them by folder to stay readable. Interactive: `gnost open flow`.)

---

<sub>Generated by [GNOST](https://gnost.readthedocs.io) 0.7.0. Try it on your own code: `uvx gnost onboard .`</sub>
