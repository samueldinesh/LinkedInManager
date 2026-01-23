# LinkedIn AI Manager - System Design

## 1. Overview
The **LinkedIn AI Manager** is an autonomous content creation system that leverages a **multi-model Intelligent API Pool** (Gemini & Gemma) to discover trends, strategize content, and generate viral LinkedIn posts.

## 2. Architecture

### Core Components
1.  **Orchestrator (`core/orchestrator.py`)**: The central brain that manages the workflow state, handles errors, and coordinates agents.
2.  **Plugin Manager (`core/plugin_manager.py`)**: Dynamically loads LLM and Search providers.
3.  **API Pool (`core/api_pool.py`)**: 
    -   Manages multiple AI models simultaneously.
    -   **Routing**: Uses "Priority" strategy (Gemma 27B Primary -> Gemma 4B Backup -> Gemini 2.0 Fallback).
    -   **Quota**: Tracks Daily Quota and automatically switches models if one fails (429/Exhausted).
4.  **Rate Limiter (`core/rate_limiter.py`)**: Prevents API flooding.

### Data Flow
```mermaid
graph TD
    User[Dashboard UI] -->|Run Workflow| Orchestrator
    Orchestrator -->|Step 1| TrendAgent
    Orchestrator -->|Step 2| StrategyAgent
    Orchestrator -->|Step 3| WritingTeam
    
    TrendAgent -->|Query| APIPool
    StrategyAgent -->|Query| APIPool
    WritingTeam -->|Query| APIPool
    
    APIPool -->|Primary| Gemma(27B)
    APIPool -->|Backup| Gemma(4B)
    APIPool -->|Fallback| Gemini(2.0)
    
    TrendAgent -->|Save| DB[(SQLite)]
    StrategyAgent -->|Save| DB
    WritingTeam -->|Save| DB
    WritingTeam -->|Save| DB
38: 
39: ### Content Automation Workflow (`agents/workflow.py`)
40: The automation system orchestrates the agents in a sequential pipeline:
41: 1.  **Trend Discovery**: Runs `TrendDiscoveryAgent` to find relevant topics (via simulated search or future RSS).
42: 2.  **Content Strategy**: Runs `ContentStrategyAgent` to ingest trends and produce specific `WeeklyPlan` with post hooks.
43: 3.  **Writing Team**: Runs `WritingTeam` to pick up draft hooks and generate full LinkedIn-optimized content.
44: 
45: ### LinkedIn Integration
46: -   **OAuth 2.0**: Handles "Sign in with LinkedIn" using `openid`, `profile`, `email`, `w_member_social` scopes.
47: -   **Posting**: Publishes approved content directly to LinkedIn profile.
48: -   **Status Tracking**: Two-way sync of connection status and posting success/failure.

## 3. Key Features

### 🧠 Intelligent Model Selection
The system uses a tiered priority system to maximize quality while minimizing cost/errors:
-   **Priority 100**: `gemma-3-27b-it` (High Quality, 1500 RPD)
-   **Priority 95**: `gemma-3-12b-it`
-   **Priority 90**: `gemma-3-4b-it`
-   **Priority 50**: `gemini-2.0-flash` (20 RPD, Fallback)

### 🚦 Dashboard & UX
-   **Real-Time Console**: AJAX-based polling shows live workflow logs without page reloads.
-   **Full CMS**: 
    -   **Edit**: Modify drafts manually.
    -   **Improve**: One-click AI enhancement of posts.
    -   **Revoke**: Revert approved posts to draft for editing.
    -   **Bulk Actions**: Delete multiple posts at once.

### 🛡️ Robustness
-   **Lazy Loading**: Agents are imported only when needed to prevent circular dependencies.
-   **Error Handling**: comprehensive try/catch blocks with user-friendly error messages.
-   **Quota Awareness**: Automatically stops or switches strategies if APIs are exhausted.

## 4. Database Schema
-   **Trends**: Stores discovered news/topics.
-   **WeeklyPlans**: High-level strategy for the week.
-   **Posts**: The actual content (Draft -> Approved -> Posted).

## 5. UI/UX Design Specs (Phase 5)

### Plan Dashboard (`/plans`)
-   **Card Layout**: Display plans as cards.
-   **Theme Badge**: Emphasize the "Theme of the Week" (e.g., "Theme: Quantum Gates") on the card.
-   **Mini-Schedule**: Show small icons/dots representing the 7 days (Part 1, News, Part 2...).

### Plan Detail View (`/plans/{id}`)
-   **Layout**: Split view into two distinct sections.
-   **Section 1: Micro-Course Series (Theme)**:
    -   Prominent header with the Theme Name.
    -   Horizontal or focused vertical list of the 3 Lesson parts.
    -   Purple styling.
-   **Section 2: News & Opportunities**:
    -   "Breaking Updates" section.
    -   Standard list/grid of News and Scheme posts.
    -   Green/Blue styling.
-   **No Duplicates**: Ensure backend appends to the single weekly plan.

## 6. Governance & Navigation (Phase 7)

### Approval Workflow
-   **Default Status**: All AI-generated content MUST start as `draft`.
-   **Approval Action**:
    -   Requres user confirmation.
    -   Inputs: `scheduled_time` (optional), `comment` (optional), `approver_name`.
-   **Posting**: Two-step verification ("Are you sure you want to post to LinkedIn?").

### Navigation Structure
-   **Main Bar**:
    -   **Dashboard** (Trends/Overview)
    -   **Course Plans** (Weekly Plans)
    -   **Topics** (Manage Content Topics)
    -   **Posts** (Review/Approve/Schedule)
-   **Settings (Dropdown/Right)**:
    -   **Providers** (LLM/Search Config)
    -   **System** (Logs/status)

## 7. Curriculum Tracker (Lesson Management)

### Concept
The system needs to track completed **Micro-Courses** and intelligently suggest the next topic to teach. This creates a continuous learning journey for the audience.

### Data Model
-   **Curriculum Table** (New):
    -   `id`, `topic_name`, `status` (planned, in_progress, completed, posted)
    -   `series_start_date`, `series_end_date`
    -   `part1_post_id`, `part2_post_id`, `part3_post_id` (Optional FKs)
    -   `audience_feedback_score` (Optional, for future engagement tracking)

### Workflow
1.  **Current Week**: AI picks a topic from `status='planned'`.
2.  **Series Completion**: When Part 3 is posted, mark curriculum as `completed`.
3.  **Next Suggestion**: AI analyzes `ContentTopics` not yet in Curriculum and suggests the next one.
4.  **User Override**: User can manually select/prioritize topics in the UI.

### UI Integration
-   **Course Plans Page**: Add a "Curriculum Progress" section showing completed, in-progress, and upcoming topics.
-   **After Posting**: Prompt user to rate engagement (optional) for future optimization.
