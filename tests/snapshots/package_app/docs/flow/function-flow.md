# Function-level Flow

What each entry point calls, function by function (Python only). Dotted arrows lead to a function already drawn elsewhere in the same diagram. Calls through other objects (`self.client.send()`) are not followed.

## `GET /chat/api/v1/messages/{message_id}` → `read_message`

`app/api/v1/chat.py:10` · 3 functions

```mermaid
flowchart LR
  app_api_v1_chat_py__read_message["read_message<br/>app/api/v1/chat.py"]
  app_services_store_py__save["save<br/>app/services/store.py"]
  app_api_v1_notes_py__helper["helper<br/>app/api/v1/notes.py"]
  app_api_v1_chat_py__read_message --> app_api_v1_notes_py__helper
  app_api_v1_chat_py__read_message --> app_services_store_py__save
```

## `POST /chat/api/v1/messages` → `send`

`app/api/v1/chat.py:15` · 3 functions

```mermaid
flowchart LR
  app_api_v1_chat_py__send["send<br/>app/api/v1/chat.py"]
  app_services_store_py__save["save<br/>app/services/store.py"]
  app_api_v1_notes_py__helper["helper<br/>app/api/v1/notes.py"]
  app_api_v1_chat_py__send --> app_api_v1_notes_py__helper
  app_api_v1_chat_py__send --> app_services_store_py__save
```

