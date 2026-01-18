# Project Tasks & Changelog

## ✅ Completed Features

### Core System
- [x] **Intelligent API Pool**: Implemented multi-provider support (Gemma + Gemini).
- [x] **Priority Routing**: Configured `gemma-3-27b-it` as primary (Priority 100).
- [x] **Plugin Architecture**: Modularized `llm_providers` and `search_providers`.

### Dashboard / UI
- [x] **Live Workflow Console**: Added real-time log streaming via AJAX (no page reloads).
- [x] **Persistent Status**: Console remains visible on Home dashboard during/after runs.
- [x] **Advanced Post Management**:
    - [x] **Edit Post**: Modal for manual content updates.
    - [x] **Improve with AI**: One-click content enhancement.
    - [x] **Revoke Approval**: Revert "Approved" posts to "Draft".
    - [x] **Bulk Delete**: Select and delete multiple posts.
- [x] **Plan Management**: Added detailed plan view and "Regenerate" option.

### Reliability & Fixes
- [x] **Circular Imports**: Fixed `ImportError` by implementing lazy loading in Orchestrator.
- [x] **Quota Management**: Solved 429 errors by correctly rotating models.
- [x] **Model Names**: Verified and corrected model names (e.g., `gemma-3-27b-it`).
- [x] **Async Database**: Fixed `AttributeError: 'coroutine' object has no attribute 'scalars'` in `WritingTeam`.
- [x] **JSON Parsing**: Fixed `JSONDecodeError` by stripping Markdown from LLM responses in `ContentStrategy`.
- [x] **Logger**: Fixed `NameError: name 'logger' is not defined` in `main.py`.

## 🚀 Known "Bug Fixes" (Reference)
- **Fix 1**: `WritingTeam` now correctly awaits `session.execute()` before calling `.scalars()`.
- **Fix 2**: `ContentStrategy` robustly handles Markdown code blocks in JSON responses.
- **Fix 3**: `Orchestrator` uses lazy imports to prevent circular dependency with Agents.
- **Fix 4**: `GeminiProvider` and `GemmaProvider` use verified model names.

## 🔜 Next Steps / Backlog
- [ ] Implement LinkedIn API integration (Oauth).
- [ ] Add "Tone of Voice" configuration to Settings.
- [ ] Add Image Generation for posts.
