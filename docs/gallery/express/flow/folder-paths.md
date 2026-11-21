# Keyword-based Execution Paths

These diagrams show execution flows related to key features, auto-detected from the project structure.

## Feature: `auth`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_auth_index_js["examples/auth/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_auth_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/auth/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

### Combined Flow (All `auth` Paths)

```mermaid
flowchart LR
  examples_auth_index_js["examples/auth/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_auth_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `content-negotiation`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_content_negotiation_index_js["examples/content-negotiation/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_content_negotiation_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/content-negotiation/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_content_negotiation_db_js["examples/content-negotiation/db.js"]
  examples_content_negotiation_index_js["examples/content-negotiation/index.js"]
  examples_content_negotiation_index_js --> examples_content_negotiation_db_js
```
**Execution chain:** examples/content-negotiation/index.js → examples/content-negotiation/db.js

### Combined Flow (All `content-negotiation` Paths)

```mermaid
flowchart LR
  examples_content_negotiation_db_js["examples/content-negotiation/db.js"]
  examples_content_negotiation_index_js["examples/content-negotiation/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_content_negotiation_index_js --> examples_content_negotiation_db_js
  examples_content_negotiation_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `cookie-sessions`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_cookie_sessions_index_js["examples/cookie-sessions/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_cookie_sessions_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/cookie-sessions/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

### Combined Flow (All `cookie-sessions` Paths)

```mermaid
flowchart LR
  examples_cookie_sessions_index_js["examples/cookie-sessions/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_cookie_sessions_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `cookies`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_cookies_index_js["examples/cookies/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_cookies_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/cookies/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

### Combined Flow (All `cookies` Paths)

```mermaid
flowchart LR
  examples_cookies_index_js["examples/cookies/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_cookies_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `downloads`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_downloads_index_js["examples/downloads/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_downloads_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/downloads/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

### Combined Flow (All `downloads` Paths)

```mermaid
flowchart LR
  examples_downloads_index_js["examples/downloads/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_downloads_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `error`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_error_pages_index_js["examples/error-pages/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_error_pages_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/error-pages/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_error_index_js["examples/error/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_error_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/error/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

### Combined Flow (All `error` Paths)

```mermaid
flowchart LR
  examples_error_pages_index_js["examples/error-pages/index.js"]
  examples_error_index_js["examples/error/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_error_pages_index_js --> index_js
  examples_error_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `multi-router`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_multi_router_index_js["examples/multi-router/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_multi_router_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/multi-router/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_multi_router_controllers_api_v1_js["examples/multi-router/controllers/api_v1.js"]
  examples_multi_router_index_js["examples/multi-router/index.js"]
  examples_multi_router_index_js --> examples_multi_router_controllers_api_v1_js
```
**Execution chain:** examples/multi-router/index.js → examples/multi-router/controllers/api_v1.js

### Combined Flow (All `multi-router` Paths)

```mermaid
flowchart LR
  examples_multi_router_controllers_api_v1_js["examples/multi-router/controllers/api_v1.js"]
  examples_multi_router_controllers_api_v2_js["examples/multi-router/controllers/api_v2.js"]
  examples_multi_router_index_js["examples/multi-router/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_multi_router_index_js --> examples_multi_router_controllers_api_v1_js
  examples_multi_router_index_js --> examples_multi_router_controllers_api_v2_js
  examples_multi_router_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `mvc`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_mvc_index_js["examples/mvc/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_mvc_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/mvc/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_mvc_index_js["examples/mvc/index.js"]
  examples_mvc_lib_boot_js["examples/mvc/lib/boot.js"]
  examples_mvc_index_js --> examples_mvc_lib_boot_js
```
**Execution chain:** examples/mvc/index.js → examples/mvc/lib/boot.js

### Combined Flow (All `mvc` Paths)

```mermaid
flowchart LR
  examples_mvc_index_js["examples/mvc/index.js"]
  examples_mvc_lib_boot_js["examples/mvc/lib/boot.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_mvc_index_js --> examples_mvc_lib_boot_js
  examples_mvc_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `route-separation`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_route_separation_index_js["examples/route-separation/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_route_separation_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/route-separation/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_route_separation_index_js["examples/route-separation/index.js"]
  examples_route_separation_post_js["examples/route-separation/post.js"]
  examples_route_separation_index_js --> examples_route_separation_post_js
```
**Execution chain:** examples/route-separation/index.js → examples/route-separation/post.js

### Combined Flow (All `route-separation` Paths)

```mermaid
flowchart LR
  examples_route_separation_index_js["examples/route-separation/index.js"]
  examples_route_separation_post_js["examples/route-separation/post.js"]
  examples_route_separation_site_js["examples/route-separation/site.js"]
  examples_route_separation_user_js["examples/route-separation/user.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_route_separation_index_js --> examples_route_separation_post_js
  examples_route_separation_index_js --> examples_route_separation_site_js
  examples_route_separation_index_js --> examples_route_separation_user_js
  examples_route_separation_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `session`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_cookie_sessions_index_js["examples/cookie-sessions/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_cookie_sessions_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/cookie-sessions/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_session_index_js["examples/session/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_session_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/session/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

### Combined Flow (All `session` Paths)

```mermaid
flowchart LR
  examples_cookie_sessions_index_js["examples/cookie-sessions/index.js"]
  examples_session_index_js["examples/session/index.js"]
  examples_session_redis_js["examples/session/redis.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_cookie_sessions_index_js --> index_js
  examples_session_index_js --> index_js
  examples_session_redis_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `view-constructor`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_view_constructor_index_js["examples/view-constructor/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_view_constructor_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/view-constructor/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_view_constructor_github_view_js["examples/view-constructor/github-view.js"]
  examples_view_constructor_index_js["examples/view-constructor/index.js"]
  examples_view_constructor_index_js --> examples_view_constructor_github_view_js
```
**Execution chain:** examples/view-constructor/index.js → examples/view-constructor/github-view.js

### Combined Flow (All `view-constructor` Paths)

```mermaid
flowchart LR
  examples_view_constructor_github_view_js["examples/view-constructor/github-view.js"]
  examples_view_constructor_index_js["examples/view-constructor/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_view_constructor_index_js --> examples_view_constructor_github_view_js
  examples_view_constructor_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

## Feature: `view-locals`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_view_locals_index_js["examples/view-locals/index.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_view_locals_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```
**Execution chain:** examples/view-locals/index.js → index.js → lib/express.js → lib/application.js → lib/utils.js

#### Path Group 2

```mermaid
flowchart LR
  examples_view_locals_index_js["examples/view-locals/index.js"]
  examples_view_locals_user_js["examples/view-locals/user.js"]
  examples_view_locals_index_js --> examples_view_locals_user_js
```
**Execution chain:** examples/view-locals/index.js → examples/view-locals/user.js

### Combined Flow (All `view-locals` Paths)

```mermaid
flowchart LR
  examples_view_locals_index_js["examples/view-locals/index.js"]
  examples_view_locals_user_js["examples/view-locals/user.js"]
  index_js["index.js"]
  lib_application_js["lib/application.js"]
  lib_express_js["lib/express.js"]
  lib_request_js["lib/request.js"]
  lib_response_js["lib/response.js"]
  lib_utils_js["lib/utils.js"]
  lib_view_js["lib/view.js"]
  examples_view_locals_index_js --> examples_view_locals_user_js
  examples_view_locals_index_js --> index_js
  index_js --> lib_express_js
  lib_application_js --> lib_utils_js
  lib_application_js --> lib_view_js
  lib_express_js --> lib_application_js
  lib_express_js --> lib_request_js
  lib_express_js --> lib_response_js
```

---

<sub>Generated by [GNOST](https://gnost.readthedocs.io) 0.5.3. Try it on your own code: `npx gnost-cli onboard .`</sub>
